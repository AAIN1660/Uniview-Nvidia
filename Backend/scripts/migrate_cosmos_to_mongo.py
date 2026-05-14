"""
One-time data migration: Azure Cosmos DB  ->  MongoDB Community Edition.
========================================================================

Counterpart to the Azure SQL -> SQL Server migration script we wrote earlier.
Re-runnable / idempotent: the destination collections are dropped before each
run, so re-running the script gives a clean reload from Cosmos.

Usage
-----
1. Make sure Backend/unified.env has BOTH backends configured side-by-side
   (the Cosmos block is what we read from; the Mongo block is what we write
   to):

       METADATA_BACKEND=mongo
       MONGO_URI=mongodb://localhost:27017
       MONGO_DATABASE_NAME=unified_prod_db

       COSMOS_ENDPOINT  = https://...
       COSMOS_KEY       = ...
       COSMOS_DATABASE_NAME = 'unified_prod_db'

2. Run from the Backend directory so unified.env is picked up:

       cd Backend
       python scripts/migrate_cosmos_to_mongo.py

3. Verify the counts printed at the end match what you see in Compass:
   mongodb://localhost:27017 -> unified_prod_db -> <collection>.

What the script does
--------------------
* Reads every document from each of the Cosmos containers used by this
  codebase (gi_users, transactions, config, gi_category, gi_qa, gi_uploads,
  db_connection, data_dictionary).
* Mirrors Cosmos 'id' onto Mongo '_id' so the Cosmos-API wrapper keeps using
  the same primary key without any translation.
* Drops the target collection before re-bulk-loading, so reruns are safe.
* Re-creates the most-used indexes (email, file_name, host,
  db_connection_id, transaction_ts, createdAt) so query performance lines up
  with Cosmos out of the box.

Safety
------
The script ONLY READS from Cosmos. The Azure data is never modified. To roll
back the cutover, flip METADATA_BACKEND=cosmos; the Cosmos containers stay
intact.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient, ReplaceOne


def _clean(v):
    if v is None:
        return None
    v = str(v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    return v


# -----------------------------------------------------------------------------
# Config / env loading
# -----------------------------------------------------------------------------
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
load_dotenv(_BACKEND / "unified.env")

COSMOS_ENDPOINT = _clean(os.getenv("COSMOS_ENDPOINT"))
COSMOS_KEY      = _clean(os.getenv("COSMOS_KEY"))
COSMOS_DB       = _clean(os.getenv("COSMOS_DATABASE_NAME")) or "unified_prod_db"

MONGO_URI = _clean(os.getenv("MONGO_URI")) or "mongodb://localhost:27017"
MONGO_DB  = _clean(os.getenv("MONGO_DATABASE_NAME")) or "unified_prod_db"

# Every Cosmos container this codebase reads/writes today.  Add new
# containers here when they're introduced and the script will pick them up
# without further changes.
CONTAINERS: list[str] = [
    "gi_users",
    "transactions",
    "config",
    "gi_category",
    "gi_qa",
    "gi_uploads",
    "db_connection",
    "data_dictionary",
]

# Per-collection indexes that mirror the most-frequent Cosmos query patterns
# we audited in the codebase.  These are non-unique by default; only `email`
# on `gi_users` is unique (Cosmos used a single-row-per-email convention).
INDEXES: dict[str, list[tuple]] = {
    "gi_users":        [(("email", ASCENDING), {"unique": True})],
    "transactions":    [(("email", ASCENDING), {}),
                        (("transaction_ts", DESCENDING), {}),
                        (("surr_no", DESCENDING), {})],
    "gi_qa":           [(("createdBy", ASCENDING), {}),
                        (("createdAt", DESCENDING), {}),
                        (("feedback", ASCENDING), {})],
    "gi_uploads":      [(("file_name", ASCENDING), {}),
                        (("category_id", ASCENDING), {}),
                        (("uploaded_by", ASCENDING), {})],
    "gi_category":     [(("status", ASCENDING), {})],
    "db_connection":   [(("host", ASCENDING), {}),
                        (("numeric_id", DESCENDING), {})],
    "data_dictionary": [(("db_connection_id", ASCENDING), {})],
}


# -----------------------------------------------------------------------------
# Migration core
# -----------------------------------------------------------------------------
def _connect_cosmos():
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        print("[ERROR] COSMOS_ENDPOINT / COSMOS_KEY missing in unified.env", file=sys.stderr)
        sys.exit(2)
    try:
        from azure.cosmos import CosmosClient
    except Exception as e:  # pragma: no cover
        print(f"[ERROR] azure-cosmos is not installed: {e}", file=sys.stderr)
        sys.exit(2)
    return CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY).get_database_client(COSMOS_DB)


def _connect_mongo():
    client = MongoClient(MONGO_URI, uuidRepresentation="standard")
    # Fail fast if MongoDB isn't running.
    client.admin.command("ping")
    return client[MONGO_DB]


def _migrate_container(cosmos_db, mongo_db, name: str) -> int:
    src = cosmos_db.get_container_client(name)
    dst = mongo_db[name]

    # Drop destination for idempotency (the script can be re-run any time).
    dst.drop()

    started = time.time()
    docs = []
    skipped_no_id = 0
    for doc in src.read_all_items():
        if "id" not in doc:
            skipped_no_id += 1
            continue
        # Mirror Cosmos 'id' -> Mongo '_id' so the wrapper keeps working
        # transparently and reads via either key stay consistent.
        mongo_doc = {**doc, "_id": doc["id"]}
        docs.append(mongo_doc)

    if docs:
        # Use bulk replace_one(upsert=True) so duplicates (if any survived
        # the drop) overwrite cleanly -- safer than insert_many on partial
        # reruns.
        ops = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
        dst.bulk_write(ops, ordered=False)

    # Re-create indexes documented for this collection.
    for key_spec, opts in INDEXES.get(name, []):
        try:
            dst.create_index([key_spec], **opts)
        except Exception as e:
            print(f"  [warn] index {key_spec} on {name} failed: {e}")

    elapsed = time.time() - started
    print(
        f"[{name:18s}] migrated {len(docs):6d} docs "
        f"(skipped {skipped_no_id} without 'id') in {elapsed:6.2f}s"
    )
    return len(docs)


def main() -> int:
    print("=" * 72)
    print("Cosmos DB -> MongoDB Community Edition  one-shot migration")
    print("-" * 72)
    print(f"  source    : Cosmos DB '{COSMOS_DB}'  @  {COSMOS_ENDPOINT}")
    print(f"  target    : MongoDB   '{MONGO_DB}'    @  {MONGO_URI}")
    print(f"  containers: {', '.join(CONTAINERS)}")
    print("=" * 72)

    cosmos_db = _connect_cosmos()
    mongo_db = _connect_mongo()

    total = 0
    for name in CONTAINERS:
        try:
            total += _migrate_container(cosmos_db, mongo_db, name)
        except Exception as e:
            print(f"[ERROR] {name}: {e}")

    print("-" * 72)
    print(f"DONE -- {total} docs migrated across {len(CONTAINERS)} collections.")
    print(
        f"Verify in MongoDB Compass:  mongodb://localhost:27017  ->  {MONGO_DB}"
    )
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
