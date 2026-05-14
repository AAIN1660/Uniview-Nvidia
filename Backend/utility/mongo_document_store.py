"""
MongoDB Community Edition adapter for Azure Cosmos DB SQL-API.
================================================================

Drop-in replacement for the subset of ``azure.cosmos`` used in this codebase.
The goal is **zero caller changes**: every router/service that already calls
``container.read_item(...)``, ``container.query_items(...)``,
``container.upsert_item(...)`` etc. keeps working when the backend is flipped
to MongoDB via ``METADATA_BACKEND=mongo`` in ``unified.env``.

Entry point
-----------
``get_database(name=None)`` returns a :class:`_MongoDatabaseProxy` that
exposes ``get_container_client(name)`` -- same method ``DatabaseProxy`` has on
the Cosmos side.

Identifier mirroring
--------------------
Cosmos uses a top-level ``id`` field as the doc identifier; MongoDB uses
``_id``.  Every write here mirrors ``body["id"] -> body["_id"]`` so writes
remain idempotent on the Cosmos primary key, and every read strips ``_id``
back out so callers continue using ``doc["id"]`` unchanged.

Exception translation
---------------------
Insert collisions are re-raised as ``azure.cosmos.exceptions.CosmosResourceExistsError``
and missing reads as ``CosmosResourceNotFoundError`` so existing
``try / except exceptions.Cosmos...`` blocks keep working.

SQL ? Mongo translator
----------------------
``query_items`` accepts the *original* Cosmos SQL string plus ``parameters``
(Cosmos format) and converts them into a ``pymongo`` filter via
:func:`_translate_sql_to_mongo`.  The translator only covers the predicate
shapes this codebase actually emits today; anything outside that set should
pass ``find_filter=<dict>`` to bypass parsing.

Rollback
--------
Setting ``METADATA_BACKEND=cosmos`` in ``unified.env`` reverts to Azure Cosmos
DB with no code change required -- same backend-flag pattern used for
``VECTOR_SEARCH_BACKEND``.
"""

from __future__ import annotations

import os
import re
from typing import Any, Iterator, Mapping

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

# Cosmos exception types are imported lazily so this module also loads when
# azure-cosmos is uninstalled (post-cleanup phase 8).  See _cosmos_exc().
try:  # pragma: no cover - import guarded for forward compatibility
    from azure.cosmos import exceptions as _cosmos_exceptions  # type: ignore
except Exception:  # pragma: no cover
    _cosmos_exceptions = None  # type: ignore


# =============================================================================
# Connection / database factory
# =============================================================================
_MONGO_CLIENT: MongoClient | None = None


def _clean_env(v: str | None) -> str | None:
    """Strip surrounding quotes / whitespace from .env values (mirrors helper)."""
    if v is None:
        return None
    v = str(v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    return v


def _get_client() -> MongoClient:
    """Process-wide MongoClient (lazy, thread-safe by pymongo design)."""
    global _MONGO_CLIENT
    if _MONGO_CLIENT is None:
        uri = _clean_env(os.getenv("MONGO_URI")) or "mongodb://localhost:27017"
        _MONGO_CLIENT = MongoClient(uri, uuidRepresentation="standard")
    return _MONGO_CLIENT


def get_database(name: str | None = None) -> "_MongoDatabaseProxy":
    """Return a Cosmos-compatible DatabaseProxy for the given database name."""
    db_name = _clean_env(name) or _clean_env(os.getenv("MONGO_DATABASE_NAME")) or "unified_prod_db"
    return _MongoDatabaseProxy(_get_client()[db_name])


# =============================================================================
# DatabaseProxy stand-in
# =============================================================================
class _MongoDatabaseProxy:
    """Stand-in for ``azure.cosmos.DatabaseProxy``."""

    def __init__(self, db: Database):
        self._db = db
        self._name = db.name

    @property
    def id(self) -> str:
        return self._name

    def read(self) -> dict:
        """Cosmos-compatible database read -- round-trip ping."""
        info = self._db.client.admin.command("ping")
        return {"id": self._name, "ok": info.get("ok")}

    def get_container_client(self, name: str) -> "CosmosLikeContainer":
        if not isinstance(name, str):
            # In Cosmos you can pass a ContainerProxy here too; we don't.
            raise TypeError(f"get_container_client expected str, got {type(name)}")
        return CosmosLikeContainer(self._db[name])

    def create_container_if_not_exists(
        self, id: str, partition_key: Any = None, **_: Any
    ) -> "CosmosLikeContainer":
        # MongoDB auto-creates collections on first write; no-op here is fine.
        return CosmosLikeContainer(self._db[id])


# =============================================================================
# ContainerProxy stand-in
# =============================================================================
class CosmosLikeContainer:
    """
    Cosmos-API-compatible wrapper around a :class:`pymongo.collection.Collection`.

    Implements every method this repo calls today:
      * ``read``
      * ``read_item(item, partition_key=None)``
      * ``query_items(query, parameters=None, enable_cross_partition_query=True,
                       max_item_count=None, find_filter=None, ...)``
      * ``read_all_items()``
      * ``upsert_item(body)``
      * ``create_item(body)``
      * ``replace_item(item, body)``  -- ``item`` may be a string id or a dict
      * ``delete_item(item, partition_key=None)``  -- ``item`` may be a string id or dict
    """

    def __init__(self, collection: Collection):
        self._c = collection
        self._name = collection.name

    @property
    def id(self) -> str:
        return self._name

    def read(self) -> dict:
        """Cheap round-trip -- Cosmos returns container metadata; we just ping."""
        list(self._c.list_indexes())
        return {"id": self._name}

    # -----------------------------------------------------------------
    # Reads
    # -----------------------------------------------------------------
    def read_item(self, item: str, partition_key: Any = None, **_: Any) -> dict:
        # Look up by mirrored _id first (the canonical id we write), then fall
        # back to a stray ``id`` field for any rows migrated from outside this
        # adapter.
        doc = self._c.find_one({"_id": item})
        if doc is None:
            doc = self._c.find_one({"id": item})
        if doc is None:
            raise _cosmos_exc(
                "CosmosResourceNotFoundError",
                f"Item with id {item!r} not found in {self._name!r}",
                status_code=404,
            )
        return _expose(doc)

    def read_all_items(self, **_: Any) -> Iterator[dict]:
        for doc in self._c.find({}):
            yield _expose(doc)

    def query_items(
        self,
        query: str | None = None,
        parameters: list[dict] | None = None,
        enable_cross_partition_query: bool = True,  # ignored: Mongo has no partitions
        max_item_count: int | None = None,
        partition_key: Any = None,                  # ignored
        find_filter: Mapping[str, Any] | None = None,
        **_: Any,
    ) -> Iterator[dict]:
        """
        Execute a Cosmos SQL query against the MongoDB collection.

        Pass ``find_filter=<dict>`` to skip the SQL translator entirely (use
        when the SQL shape is too complex for ``_translate_sql_to_mongo``).
        """
        if find_filter is not None:
            spec = {
                "filter": dict(find_filter),
                "projection": None,
                "sort": None,
                "limit": max_item_count,
                "aggregate": None,
                "unwrap_value": False,
            }
        else:
            spec = _translate_sql_to_mongo(query or "", parameters or [])
            if max_item_count and spec.get("limit") is None:
                spec["limit"] = max_item_count

        if spec.get("aggregate"):
            for doc in self._c.aggregate(spec["aggregate"]):
                if spec.get("unwrap_value"):
                    # Cosmos `SELECT VALUE MAX(...)` returns raw scalars; mimic.
                    yield doc.get("value")
                else:
                    yield _expose(doc)
            return

        cursor = self._c.find(spec["filter"] or {}, spec.get("projection"))
        if spec.get("sort"):
            cursor = cursor.sort(spec["sort"])
        if spec.get("limit"):
            cursor = cursor.limit(int(spec["limit"]))
        for doc in cursor:
            yield _expose(doc)

    # -----------------------------------------------------------------
    # Writes
    # -----------------------------------------------------------------
    def upsert_item(self, body: Mapping[str, Any], **_: Any) -> dict:
        doc = _prepare_for_write(body, require_id=True)
        self._c.replace_one({"_id": doc["_id"]}, doc, upsert=True)
        return _expose(doc)

    def create_item(self, body: Mapping[str, Any], **_: Any) -> dict:
        doc = _prepare_for_write(body, require_id=True)
        try:
            self._c.insert_one(doc)
        except DuplicateKeyError as e:
            raise _cosmos_exc(
                "CosmosResourceExistsError",
                f"Item with id {doc.get('_id')!r} already exists in {self._name!r}",
                status_code=409,
            ) from e
        return _expose(doc)

    def replace_item(
        self,
        item: Any,
        body: Mapping[str, Any],
        **_: Any,
    ) -> dict:
        # Cosmos accepts either a string id OR the full doc -- we handle both.
        item_id = item["id"] if isinstance(item, Mapping) else item
        doc = _prepare_for_write(body, require_id=False)
        doc["_id"] = item_id
        doc["id"] = item_id
        result = self._c.replace_one({"_id": item_id}, doc, upsert=False)
        if result.matched_count == 0:
            raise _cosmos_exc(
                "CosmosResourceNotFoundError",
                f"Cannot replace -- item with id {item_id!r} not found in {self._name!r}",
                status_code=404,
            )
        return _expose(doc)

    def delete_item(self, item: Any, partition_key: Any = None, **_: Any) -> None:
        item_id = item["id"] if isinstance(item, Mapping) else item
        self._c.delete_one({"_id": item_id})


# =============================================================================
# Helpers -- Cosmos / Mongo interop
# =============================================================================
def _expose(doc: Mapping[str, Any]) -> dict:
    """Hide MongoDB's internal ``_id`` from callers; expose only ``id``."""
    out = dict(doc)
    out.pop("_id", None)
    return out


def _prepare_for_write(body: Mapping[str, Any], *, require_id: bool) -> dict:
    """Mirror ``body['id']`` onto ``body['_id']`` so Mongo enforces the same PK."""
    doc = dict(body)
    if "id" in doc:
        doc["_id"] = doc["id"]
    elif require_id:
        raise ValueError(
            "Cosmos-compatible write requires an 'id' field in the body."
        )
    return doc


def _cosmos_exc(name: str, message: str, status_code: int) -> Exception:
    """
    Build a Cosmos-style exception so existing ``except exceptions.X`` blocks
    keep working.  Falls back to a generic ``RuntimeError`` if azure-cosmos is
    no longer installed (post-cleanup Phase 8).
    """
    if _cosmos_exceptions is None:
        return RuntimeError(f"[{name}] {message}")
    cls = getattr(_cosmos_exceptions, name, None) or getattr(
        _cosmos_exceptions, "CosmosHttpResponseError"
    )
    try:
        return cls(message=message, status_code=status_code)
    except TypeError:
        return cls(message)


# =============================================================================
# Cosmos-SQL  ?  MongoDB filter translator
# -----------------------------------------------------------------------------
# Covers every shape this repo emits today (audited 2026-05-14):
#
#   SELECT * FROM c
#   SELECT * FROM <table> <alias>
#   SELECT <fields> FROM c [WHERE ...] [ORDER BY ...]
#   SELECT TOP N <fields> FROM c [WHERE ...] [ORDER BY ...]
#   SELECT VALUE MAX(c.field) FROM c
#
#   WHERE predicates:
#     field = value          ? {field: value}
#     field != value | <>    ? {field: {"$ne": value}}
#     field IN (v1, v2, ...) ? {field: {"$in": [...]}}
#     ARRAY_CONTAINS(arr, v) ? {arr: v}            (Mongo matches array members)
#     IS_DEFINED(field)      ? {field: {"$exists": True}}
#     field = []             ? {field: {"$in": [[], None]}}
#
#   Multiple AND-joined predicates ? {"$and": [...]}
#   Top-level OR is intentionally unsupported -- pass find_filter= instead.
#
# Anything outside this set should bypass the translator with
#     container.query_items(query, parameters=..., find_filter={...})
# =============================================================================

_ALIAS_RX = re.compile(r"^\s*\w+\.")          # 'c.', 't.', 'r.', etc.
_COMMENT_RX = re.compile(r"--.*?$", re.MULTILINE)
_VALUE_MAX_RX = re.compile(
    r"^\s*SELECT\s+VALUE\s+MAX\s*\(\s*([\w\.\[\]]+)\s*\)\s+FROM\s+\w+(?:\s+\w+)?\s*;?\s*$",
    re.IGNORECASE,
)
_SELECT_RX = re.compile(
    r"^\s*SELECT\s+(?P<top>TOP\s+\d+\s+)?(?P<proj>.+?)\s+FROM\s+\w+(?:\s+\w+)?"
    r"(?:\s+WHERE\s+(?P<where>.+?))?"
    r"(?:\s+ORDER\s+BY\s+(?P<order>.+?))?"
    r"\s*;?\s*$",
    re.IGNORECASE | re.DOTALL,
)


def _strip_alias(field: str) -> str:
    """Drop a single-token alias prefix: 'c.email' -> 'email'."""
    return _ALIAS_RX.sub("", field, count=1).strip()


def _coerce_literal(token: str, params: dict) -> Any:
    """Convert a SQL literal / parameter reference into a Python value."""
    token = token.strip()
    if not token:
        return None
    if token.startswith("@"):
        return params.get(token[1:])
    if len(token) >= 2 and token[0] == token[-1] and token[0] in ("'", '"'):
        return token[1:-1]
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        pass
    lc = token.lower()
    if lc in ("true", "false"):
        return lc == "true"
    if lc == "null":
        return None
    return token


def _build_params_map(parameters: list[dict]) -> dict:
    """Convert Cosmos parameter list to a {name: value} dict."""
    out: dict[str, Any] = {}
    for p in parameters or []:
        name = p.get("name") or ""
        if name.startswith("@"):
            name = name[1:]
        out[name] = p.get("value")
    return out


def _split_csv(s: str) -> list[str]:
    """Split a comma-separated list while honouring quotes and brackets."""
    parts: list[str] = []
    cur = ""
    depth = 0
    in_str: str | None = None
    for ch in s:
        if in_str:
            cur += ch
            if ch == in_str:
                in_str = None
        elif ch in ("'", '"'):
            in_str = ch
            cur += ch
        elif ch in "([":
            depth += 1
            cur += ch
        elif ch in ")]":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _parse_where_clause(where_text: str, params: dict) -> dict:
    """Convert a Cosmos WHERE clause into a MongoDB filter dict."""
    if not where_text.strip():
        return {}

    # Top-level OR isn't supported -- callers should pass find_filter= explicitly.
    if re.search(r"\s+or\s+", where_text, re.IGNORECASE):
        raise NotImplementedError(
            f"Top-level OR is not supported by the SQL?Mongo translator. "
            f"Pass find_filter= on this call site. Query fragment: {where_text!r}"
        )

    conditions: list[dict] = []
    for raw in re.split(r"\s+AND\s+", where_text, flags=re.IGNORECASE):
        clause = raw.strip()
        if not clause:
            continue

        # ARRAY_CONTAINS(field, value)
        m = re.match(
            r"ARRAY_CONTAINS\s*\(\s*([\w\.\[\]]+)\s*,\s*(.+?)\s*\)\s*$",
            clause, re.IGNORECASE,
        )
        if m:
            field = _strip_alias(m.group(1))
            val = _coerce_literal(m.group(2), params)
            conditions.append({field: val})
            continue

        # IS_DEFINED(field)
        m = re.match(
            r"IS_DEFINED\s*\(\s*([\w\.\[\]]+)\s*\)\s*$",
            clause, re.IGNORECASE,
        )
        if m:
            field = _strip_alias(m.group(1))
            conditions.append({field: {"$exists": True}})
            continue

        # field IN (v1, v2, ...)
        m = re.match(
            r"([\w\.\[\]]+)\s+IN\s*\(\s*(.+?)\s*\)\s*$",
            clause, re.IGNORECASE | re.DOTALL,
        )
        if m:
            field = _strip_alias(m.group(1))
            values = [_coerce_literal(v, params) for v in _split_csv(m.group(2))]
            conditions.append({field: {"$in": values}})
            continue

        # field != value  /  field <> value
        m = re.match(r"([\w\.\[\]]+)\s*(?:!=|<>)\s*(.+?)\s*$", clause)
        if m:
            field = _strip_alias(m.group(1))
            val = _coerce_literal(m.group(2), params)
            conditions.append({field: {"$ne": val}})
            continue

        # field = value
        m = re.match(r"([\w\.\[\]]+)\s*=\s*(.+?)\s*$", clause)
        if m:
            field = _strip_alias(m.group(1))
            raw_val = m.group(2).strip()
            if raw_val == "[]":
                # Cosmos `field = []` matches docs whose array field is empty
                # OR missing.  Mirror that.
                conditions.append({field: {"$in": [[], None]}})
                continue
            val = _coerce_literal(raw_val, params)
            conditions.append({field: val})
            continue

        raise NotImplementedError(
            f"Cannot translate WHERE predicate to Mongo: {clause!r}. "
            f"Pass find_filter= explicitly on this call site."
        )

    if not conditions:
        return {}
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _translate_sql_to_mongo(query: str, parameters: list[dict]) -> dict:
    """
    Convert a Cosmos SQL query + parameter list to a Mongo execution spec.

    Returns
    -------
    dict with keys:
      ``filter``      - dict (or {} for "match everything")
      ``projection``  - dict or None
      ``sort``        - list[(field, direction)] or None
      ``limit``       - int or None
      ``aggregate``   - list[stage] or None       (set for SELECT VALUE MAX)
      ``unwrap_value``- bool                       (True for SELECT VALUE)
    """
    params = _build_params_map(parameters)
    q = _COMMENT_RX.sub("", query or "").strip()

    if not q:
        return {
            "filter": {},
            "projection": None,
            "sort": None,
            "limit": None,
            "aggregate": None,
            "unwrap_value": False,
        }

    # SELECT VALUE MAX(c.field) FROM c
    m = _VALUE_MAX_RX.match(q)
    if m:
        field = _strip_alias(m.group(1))
        pipeline = [
            {"$group": {"_id": None, "value": {"$max": f"${field}"}}},
            {"$project": {"_id": 0, "value": 1}},
        ]
        return {
            "filter": None,
            "projection": None,
            "sort": None,
            "limit": None,
            "aggregate": pipeline,
            "unwrap_value": True,
        }

    # SELECT ... FROM ... [WHERE ...] [ORDER BY ...]
    m = _SELECT_RX.match(q)
    if not m:
        raise NotImplementedError(
            f"SQL?Mongo translator can't parse this query: {q!r}. "
            f"Pass find_filter= explicitly on this call site."
        )

    # TOP N ? limit
    limit: int | None = None
    if m.group("top"):
        mt = re.match(r"TOP\s+(\d+)", m.group("top"), re.IGNORECASE)
        if mt:
            limit = int(mt.group(1))

    # Projection
    proj_text = m.group("proj").strip()
    projection: dict | None = None
    if proj_text != "*":
        fields = [_strip_alias(p.strip()) for p in _split_csv(proj_text)]
        fields = [f for f in fields if f and f != "*"]
        if fields:
            projection = {f: 1 for f in fields}
            projection["_id"] = 0  # hide Mongo's internal id

    # WHERE ? filter
    filt: dict = {}
    if m.group("where"):
        filt = _parse_where_clause(m.group("where").strip(), params)

    # ORDER BY ? sort
    sort: list[tuple[str, int]] | None = None
    if m.group("order"):
        sort = []
        for term in _split_csv(m.group("order").strip()):
            parts = term.split()
            field = _strip_alias(parts[0])
            direction = -1 if (len(parts) > 1 and parts[1].upper() == "DESC") else 1
            sort.append((field, direction))

    return {
        "filter": filt,
        "projection": projection,
        "sort": sort,
        "limit": limit,
        "aggregate": None,
        "unwrap_value": False,
    }
