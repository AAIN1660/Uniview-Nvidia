"""
Shared Cosmos DB client (lazy init + longer connection timeout).
Avoids import-time failures when Azure is slow or briefly unreachable.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from azure.cosmos import CosmosClient
from dotenv import load_dotenv

load_dotenv("unified.env")


def _clean_env(value, default=None):
    value = value if value is not None else default
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


def _connection_timeout_sec() -> int:
    raw = os.getenv("COSMOS_CONNECTION_TIMEOUT_SEC") or "60"
    try:
        return max(10, int(str(raw).strip()))
    except ValueError:
        return 60


def _enable_endpoint_discovery() -> bool:
    """When False, use only COSMOS_ENDPOINT (avoids bad regional host DNS after failover)."""
    raw = (_clean_env(os.getenv("COSMOS_ENABLE_ENDPOINT_DISCOVERY")) or "false").lower()
    return raw in ("1", "true", "yes", "on")


@lru_cache(maxsize=1)
def get_cosmos_client() -> CosmosClient:
    endpoint = _clean_env(os.getenv("COSMOS_ENDPOINT"))
    key = _clean_env(os.getenv("COSMOS_KEY"))
    if not endpoint or not key:
        raise RuntimeError("COSMOS_ENDPOINT and COSMOS_KEY must be set in unified.env")
    return CosmosClient(
        url=endpoint,
        credential=key,
        connection_timeout=_connection_timeout_sec(),
        enable_endpoint_discovery=_enable_endpoint_discovery(),
    )


@lru_cache(maxsize=1)
def get_database():
    db_name = _clean_env(os.getenv("COSMOS_DATABASE_NAME"))
    if not db_name:
        raise RuntimeError("COSMOS_DATABASE_NAME must be set in unified.env")
    return get_cosmos_client().get_database_client(db_name)


def get_container(env_var: str, default: str):
    name = _clean_env(os.getenv(env_var), default)
    return get_database().get_container_client(name)


class _LazyProxy:
    """Defer Cosmos client/container creation until first use (works with bare names)."""

    __slots__ = ("_factory", "_obj")

    def __init__(self, factory):
        object.__setattr__(self, "_factory", factory)
        object.__setattr__(self, "_obj", None)

    def _resolve(self):
        obj = object.__getattribute__(self, "_obj")
        if obj is None:
            obj = object.__getattribute__(self, "_factory")()
            object.__setattr__(self, "_obj", obj)
        return obj

    def __getattr__(self, name):
        return getattr(self._resolve(), name)


# Module-level names for routers/services (PEP 562 __getattr__ does not apply to bare names).
client = _LazyProxy(get_cosmos_client)
database = _LazyProxy(get_database)
user_container = _LazyProxy(lambda: get_container("USER_CONTAINER_NAME", "gi_users"))
transaction_container = _LazyProxy(
    lambda: get_container("TRANSACTION_CONTAINER_NAME", "transactions")
)
tran_container = transaction_container
config_container = _LazyProxy(lambda: get_container("CONFIG_CONTAINER_NAME", "config"))
upload_container = _LazyProxy(lambda: get_container("UPLOAD_CONTAINER_NAME", "gi_uploads"))
uploads_container = upload_container
qa_container = _LazyProxy(lambda: get_container("QA_CONTAINER_NAME", "gi_qa"))
feedback_container = qa_container
category_container = _LazyProxy(lambda: get_container("CATEGORY_CONTAINER_NAME", "gi_category"))
db_conn_container = _LazyProxy(lambda: get_database().get_container_client("db_connection"))
data_dictionary_container = _LazyProxy(
    lambda: get_database().get_container_client("data_dictionary")
)

_LAZY_CONTAINER_PROXIES = (
    client,
    database,
    user_container,
    transaction_container,
    config_container,
    upload_container,
    qa_container,
    category_container,
    db_conn_container,
    data_dictionary_container,
)


def reset_cosmos_connections() -> None:
    """Clear cached clients after Cosmos network / DNS errors."""
    get_cosmos_client.cache_clear()
    get_database.cache_clear()
    for proxy in _LAZY_CONTAINER_PROXIES:
        object.__setattr__(proxy, "_obj", None)
