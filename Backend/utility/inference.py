#import streamlit as st
import time
import pandas as pd
import tiktoken
import asyncio
import threading
## SQL 
import pandas as pd
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, String, Integer
import urllib
import os
import pypyodbc as odbc
import json
from typing import Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from openai import AzureOpenAI

from utility.embedding_config import (
    create_embedding_vector,
    embedding_backend,
    embedding_model_id,
    get_embedding_client,
)
import json
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
# from azure.search.documents.models import Vector
from azure.search.documents.models import (QueryAnswerType, QueryCaptionType, QueryType, VectorizedQuery   )
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_relationships,
    read_indexer_entities,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.typing import OpenaiApiType
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
from graphrag.vector_stores.lancedb import LanceDBVectorStore
import asyncio
import ast
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from utility.graphrag_artifacts import (
    expected_graph_embedding_dim,
    graph_lancedb_uri,
    resolve_graph_artifacts_folder,
    validate_entity_embedding_dims,
)
from utility.graphrag_text_embedder import create_graphrag_text_embedder, graphrag_embeddings_use_nim
from utility.helper import (
    formating_final_answer,
    get_sql_engine,
    get_sql_table_schema,
    get_tables_list_by_email,
)
# from helper import get_sql_table_schema, get_tables_list_by_email, formating_final_answer
from dotenv import load_dotenv
import tempfile
from azure.storage.blob import BlobServiceClient
import matplotlib.pyplot as plt
import io
import shutil
from pathlib import Path

load_dotenv("unified.env")

# Azure Cognitive Search configuration
AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")
AZURE_OPENAI_EMBEDDING_MODEL_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME")
GPT3_LLM_MODEL_NAME = os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME")
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

GRAPH_RAG_OPENAI_API_BASE = os.getenv("GRAPH_RAG_OPENAI_API_BASE")
GRAPH_RAG_OPENAI_API_VERSION = os.getenv("GRAPH_RAG_OPENAI_API_VERSION")
GRAPH_RAG_OPENAI_API_KEY = os.getenv("GRAPH_RAG_OPENAI_API_KEY")

azure_search_credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)


# Blob storage configuration
BLOB_CONNECTION_STRING = os.getenv("BLOB_STORAGE_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_STORAGE_CONTAINER_NAME")
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)


# GraphRAG LLM and embedding configurations
api_key = os.getenv("AZURE_OPENAI_API_KEY")
llm_model = GPT3_LLM_MODEL_NAME
embedding_model =AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL
api_base = os.getenv("AZURE_OPENAI_API_BASE")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
api_type = os.getenv("OPENAI_API_TYPE")


# # SQLdb credentials Parameters
# host = os.getenv('HOST')
# database = os.getenv('DATABASE')
# username = os.getenv('USERNAME')
# password = os.getenv('PASSWORD')
# driver = os.getenv('DRIVER')

def _clean_env(value, default=None):
    value = value if value is not None else default
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


host = _clean_env(os.getenv("SQL_HOST"))
database = _clean_env(os.getenv("SQL_DATABASE"))
username = _clean_env(os.getenv("SQL_USERNAME"))
password = _clean_env(os.getenv("SQL_PASSWORD"))
driver = _clean_env(os.getenv("SQL_DRIVER"), "ODBC Driver 18 for SQL Server")
category_name = os.getenv("SQL_SCHEMA") or "dbo"
if not all([host, database, username, password]):
    raise ValueError("SQL credentials missing. Set SQL_HOST, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD in unified.env")

table_name = ["marsdata","unified_HR_data","healthcare_patient_details","healthcare_lab_results"]

# ---------------------------------------------------------------------------
# Step 1: Connection string
# ---------------------------------------------------------------------------
# Active backend: SQL Server 2022 Developer Edition installed locally
# (native Windows install, same engine as Azure SQL Database).
# The local instance ships a self-signed cert by default, so we explicitly
# opt into `TrustServerCertificate=yes`.  These flags are harmless against
# Azure SQL (Azure forces TLS regardless), so the same line works for
# every backend we might switch to (Local SQL Server / Babelfish / Azure SQL).
#
# To switch backends, flip the credentials in unified.env — no code change
# required here.
# ---------------------------------------------------------------------------

# ----- AZURE SQL (commented out — preserved for rollback) ------------------
# connection_string = f'mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(f"DRIVER={driver};SERVER={host};DATABASE={database};UID={username};PWD={password}")}'

# ----- LOCAL SQL SERVER / BABELFISH (active) -------------------------------
# Same connection-string shape works for both — they speak TDS on port 1433
# and present a self-signed cert by default.
connection_string = (
    "mssql+pyodbc:///?odbc_connect="
    + urllib.parse.quote_plus(
        f"DRIVER={driver};"
        f"SERVER={host};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
)

# Use the shared pooled engine so all SQL paths (schema reflection, schema
# cache, ``execute_sql_tool``) share one connection pool per connection
# string. ``_ensure_engine`` adds an active health-check + rebuild so a
# stale connection mid-session can't break a long NAT run.
def _build_engine():
    return get_sql_engine(connection_string)


def _ensure_engine():
    global engine
    if engine is None:
        engine = _build_engine()
        return engine
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return engine
    except Exception:
        try:
            engine.dispose()
        except Exception:
            pass
        engine = _build_engine()
        return engine


# Create the SQLAlchemy engine
try:
    engine = _build_engine()
except Exception as _engine_exc:
    print("SQL engine initialization failed at startup:", _engine_exc)
    engine = None

# Step 2: Fetch tables from the specified schema dynamically
def get_schema_tables(engine, schema_name):
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema=schema_name)
    
    schema_details = ""
    for table_name in tables:
        columns = inspector.get_columns(table_name, schema=schema_name)
        schema = f'schema = "{schema_name}", table_name = "{schema_name}.{table_name}", {table_name}_table = Table(\n'
        for column in columns:
            col_name = column['name']
            col_type = column['type']
            primary_key = "primary_key=True" if column.get("primary_key", False) else ""
            nullable = "nullable=False" if not column["nullable"] else ""
            schema += f'    Column("{col_name}", {col_type}, {primary_key} {nullable}),\n'
        schema = schema.rstrip(',\n')  # Remove the last comma and newline
        schema += "\n)\n\n"
        schema_details += schema

    return schema_details

# Fetch tables from the dynamically specified schema
try:
    all_table_schemas = get_schema_tables(engine, category_name) if engine is not None else ""
except Exception as _schema_exc:
    print("Initial SQL schema load failed; continuing without startup schema:", _schema_exc)
    all_table_schemas = ""

print(all_table_schemas)

params = urllib.parse.quote_plus(
    f"DRIVER={driver};"
    f"SERVER={host};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)





# # LLM configuration
# llm_config = {
#     "config_list":[
#     {
#         "model": GPT3_LLM_MODEL_NAME,
#         "api_type": "azure",
#         "base_url": AZURE_OPENAI_API_BASE,
#         "api_key": AZURE_OPENAI_API_KEY,
#         "api_version":AZURE_OPENAI_API_VERSION,
#         }
# ],
#     "cache_seed": None,
#     "temperature": 0.1,
#     # "max_tokens": -1,
#     # "request_timeout": 6000
# }


# Embeddings for vector search (Azure OpenAI or NVIDIA NIM — see unified.env EMBEDDING_BACKEND)
client = get_embedding_client()

# model = os.getenv('MODEL')

NVIDIA_BASE_URL = _clean_env(os.getenv("NVIDIA_BASE_URL"), "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = _clean_env(os.getenv("NVIDIA_MODEL"), "meta/llama-3.3-70b-instruct")
NVIDIA_API_KEY = _clean_env(os.getenv("NVIDIA_API_KEY"), "")

if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY is required in unified.env")

# llm_config = {
#     "config_list": [
#         {
#             "model": NVIDIA_MODEL,
#             "api_type": "openai",
#             "base_url": NVIDIA_BASE_URL,
#             "api_key": NVIDIA_API_KEY,
#         }
#     ],
#     "cache_seed": None,
#     "temperature": 0.1,
# }

def generate_embeddings(text, client, embedding_model_deloyment_name):
    if embedding_backend() == "nvidia":
        return create_embedding_vector(client, text, input_type="query")
    embeddings = client.embeddings.create(
        input=[text], model=embedding_model_deloyment_name
    ).data[0].embedding
    return embeddings


def _vector_search_backend() -> str:
    """Hybrid/vector RAG retrieval: 'azure' (Azure AI Search) or 'zilliz' (Milvus/Zilliz via utility.zilliz_client)."""
    b = (os.getenv("VECTOR_SEARCH_BACKEND") or "azure").strip().lower()
    if b in ("zilliz", "milvus"):
        return "zilliz"
    return "azure"


search_client = SearchClient(endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,index_name=AZURE_SEARCH_INDEX_NAME,
                             credential=azure_search_credential
                             )

llm = ChatOpenAI(
    api_key=_clean_env(GRAPH_RAG_OPENAI_API_KEY or AZURE_OPENAI_API_KEY),
    api_base=_clean_env(GRAPH_RAG_OPENAI_API_BASE or AZURE_OPENAI_API_BASE),
    api_version=_clean_env(GRAPH_RAG_OPENAI_API_VERSION or AZURE_OPENAI_API_VERSION),
    deployment_name="gpt-4o",
    model=GPT3_LLM_MODEL_NAME,
    api_type=OpenaiApiType.AzureOpenAI,
    max_retries=20,
)

token_encoder = tiktoken.get_encoding("cl100k_base")


def _clean_env_val(v):
    """Strip whitespace and surrounding quotes (PowerShell env loader leaves them)."""
    if v is None:
        return ""
    return v.strip().strip('"').strip("'")


# -----------------------------------------------------------------------------
# GraphRAG entity embedder (query-time)
# -----------------------------------------------------------------------------
# Must match the model and vector dimension used when the GraphRAG index was
# built (see ``data/settings.yaml`` embeddings + ``graphrag_index_runner.py``).
# Default: NIM ``NVIDIA_EMBEDDING_MODEL`` when ``EMBEDDING_BACKEND=nvidia`` (or
# ``GRAPH_RAG_EMBEDDING_BACKEND=nvidia``). Azure path remains for legacy indices
# (set ``GRAPH_RAG_EMBEDDING_BACKEND=azure``). After switching embedding
# provider, re-run the full GraphRAG indexer.
# -----------------------------------------------------------------------------
text_embedder = create_graphrag_text_embedder()


# Localsearch_engine = LocalSearch(
#                 llm=None,
#                 context_builder=Localcontext_builder,
#                 token_encoder=token_encoder,
#                 llm_params=llm_params,
#                 context_builder_params=local_context_params,
#                 response_type="single paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
#             )



def extract_data(question, index_type, filter, explain_code, category):
    # # Extracting all 'overrides' and assigning them as global variables
    global search_type
    global category_filter
    global sql_code_explanation
    global graphrag_category
    search_type = index_type
    graphrag_category = category
    category_filter = filter
    sql_code_explanation = explain_code



# print('###########################################', connection_string)


# print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& all_table_schemas &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&', all_table_schemas)


def download_blob_to_tempfile(blob_service_client, container_name, blob_path):
    print('###############################################')
    print('container_name:', container_name)

    print('###############################################')
    print('blob_path', blob_path)


    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    with open(temp_file.name, "wb") as file:
        file.write(blob_client.download_blob().readall())
    return temp_file.name


def _download_blob_bytes(blob_service_client, container_name, blob_path) -> bytes:
    """In-memory blob fetch used by the cached GraphRAG bootstrap.

    Avoids tempfile writes that ``download_blob_to_tempfile`` performs on every
    semantic round. Bytes are passed straight into pandas via ``io.BytesIO``.
    """
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    return blob_client.download_blob().readall()


# Cache for the GraphRAG ``LocalSearchMixedContext`` builder keyed by
# (container, folder). The 5 parquet files + LanceDB connect + entity
# embedding store are immutable for a given indexed artifact set, so we
# build the context object once per process and reuse it on every
# semantic round.
_GRAPH_CONTEXT_CACHE: dict[tuple[str, str], dict[str, object]] = {}
_GRAPH_CONTEXT_LOCK = threading.Lock()
try:
    _GRAPH_CONTEXT_TTL_SEC = float(os.getenv("GRAPH_RAG_CACHE_TTL_SEC", "0") or "0")
except ValueError:
    _GRAPH_CONTEXT_TTL_SEC = 0.0


def _build_graph_context_builder(container_name: str, folder_path: str) -> LocalSearchMixedContext:
    """Heavy one-time setup for a given indexed artifact set.

    Downloads the 5 parquet files in-memory, processes entities /
    relationships / reports / text units, connects to LanceDB once,
    stores entity semantic embeddings, and returns the constructed
    ``LocalSearchMixedContext``.
    """
    COMMUNITY_REPORT_TABLE = "create_final_community_reports"
    ENTITY_TABLE = "create_final_nodes"
    ENTITY_EMBEDDING_TABLE = "create_final_entities"
    RELATIONSHIP_TABLE = "create_final_relationships"
    TEXT_UNIT_TABLE = "create_final_text_units"
    COMMUNITY_LEVEL = 3

    LANCEDB_URI = graph_lancedb_uri(folder_path)
    rebuild = _clean_env_val(os.getenv("GRAPH_RAG_REBUILD_LANCE")).lower() in ("1", "true", "yes")
    if rebuild and os.path.isdir(LANCEDB_URI):
        shutil.rmtree(LANCEDB_URI, ignore_errors=True)
    os.makedirs(LANCEDB_URI, exist_ok=True)

    expected_dim = expected_graph_embedding_dim()
    print(
        f"[GraphRAG] loading artifacts from blob:{folder_path} | "
        f"lancedb:{LANCEDB_URI} | embed_backend={'nvidia' if graphrag_embeddings_use_nim() else 'azure'} | "
        f"expected_dim={expected_dim}",
        flush=True,
    )

    def _read(table: str) -> pd.DataFrame:
        data = _download_blob_bytes(
            blob_service_client, container_name, f"{folder_path}/{table}.parquet"
        )
        return pd.read_parquet(io.BytesIO(data))

    entity_df = _read(ENTITY_TABLE)
    entity_embedding_df = _read(ENTITY_EMBEDDING_TABLE)
    relationship_df = _read(RELATIONSHIP_TABLE)
    report_df = _read(COMMUNITY_REPORT_TABLE)
    text_unit_df = _read(TEXT_UNIT_TABLE)

    relationships = read_indexer_relationships(relationship_df)
    entities = read_indexer_entities(entity_df, entity_embedding_df, COMMUNITY_LEVEL)
    validate_entity_embedding_dims(entities, expected_dim, folder_path)

    description_embedding_store = LanceDBVectorStore(collection_name="entity_description_embeddings")
    description_embedding_store.connect(db_uri=LANCEDB_URI)
    store_entity_semantic_embeddings(entities=entities, vectorstore=description_embedding_store)

    reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)
    text_units = read_indexer_text_units(text_unit_df)

    return LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        covariates=None,
        entity_text_embeddings=description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )


def _get_graph_context_builder(container_name: str, folder_path: str) -> LocalSearchMixedContext:
    """Return a cached ``LocalSearchMixedContext`` or build + cache it.

    Thread-safe via ``threading.Lock`` (build is invoked from worker
    threads via ``asyncio.to_thread`` in the caller).
    """
    key = (container_name, folder_path)
    now = time.time()
    with _GRAPH_CONTEXT_LOCK:
        entry = _GRAPH_CONTEXT_CACHE.get(key)
        if entry is not None:
            if _GRAPH_CONTEXT_TTL_SEC <= 0 or (now - float(entry["ts"])) < _GRAPH_CONTEXT_TTL_SEC:
                return entry["builder"]  # type: ignore[return-value]

    builder = _build_graph_context_builder(container_name, folder_path)

    with _GRAPH_CONTEXT_LOCK:
        _GRAPH_CONTEXT_CACHE[key] = {"builder": builder, "ts": time.time()}
    return builder


def invalidate_graph_context_cache(container_name: str | None = None, folder_path: str | None = None) -> None:
    """Drop cached builders; use after a fresh GraphRAG index is published.

    No-arg call clears everything. Pass both args to drop a single entry.
    """
    with _GRAPH_CONTEXT_LOCK:
        if container_name is None and folder_path is None:
            _GRAPH_CONTEXT_CACHE.clear()
            return
        if container_name is not None and folder_path is not None:
            _GRAPH_CONTEXT_CACHE.pop((container_name, folder_path), None)


_last_extract_context_latencies: dict[str, float | str] = {}


def pop_extract_context_latencies() -> dict[str, float | str]:
    """Sub-step timings from the most recent ``extract_context`` call (for latency tables)."""
    global _last_extract_context_latencies
    out: dict[str, float | str] = {}
    for k, v in _last_extract_context_latencies.items():
        if isinstance(v, (int, float)):
            out[k] = round(float(v), 3)
        else:
            out[k] = v
    _last_extract_context_latencies = {}
    return out


async def extract_context(question: str = None, vector_weight: float = 0.5, graph_weight: float = 0.5) -> dict:
    global _last_extract_context_latencies
    _last_extract_context_latencies = {}
    t_extract_start = time.perf_counter()

    selector = search_type
    # selector = 'hybrid'
    print('************************************** selector ******************************', selector)
    if not question:
        print("No question provided")
        return {}

    async def fetch_vector_context():
        t_vec = time.perf_counter()
        # ------------------------------------------------------------------
        # Unified retrieval path (Azure AI Search OR Milvus/Zilliz):
        #   1. Embed the question  (NVIDIA NIM nv-embedqa-e5-v5)
        #   2. Retrieve top-K candidates (oversampled, default 20)
        #         - Zilliz: dense GPU_CAGRA/AUTOINDEX + BM25 sparse hybrid (RRF)
        #         - Azure:  dense HNSW + BM25 hybrid (legacy fallback)
        #   3. Re-rank with NVIDIA NIM `llama-nemotron-rerank-1b-v2`
        #      down to RERANKER_TOP_N (default 3) — replaces Azure's
        #      QueryType.SEMANTIC server-side re-ranker so the same NVIDIA-
        #      native reranker runs regardless of which backend is active.
        # ------------------------------------------------------------------
        model = (
            embedding_model_id()
            if embedding_backend() == "nvidia"
            else os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")
        )
        t_embed = time.perf_counter()
        vector = generate_embeddings(question, client, model)
        _last_extract_context_latencies["retrieval:vector_embed_sec"] = round(
            time.perf_counter() - t_embed, 3
        )

        # Oversample for reranker. ZILLIZ_VECTOR_TOP_K kept as legacy override.
        retrieve_top_k_raw = (
            os.getenv("RETRIEVE_TOP_K")
            or os.getenv("ZILLIZ_VECTOR_TOP_K")
            or os.getenv("VECTOR_TOP_K")
            or "20"
        )
        try:
            retrieve_top_k = max(1, int(str(retrieve_top_k_raw).strip()))
        except ValueError:
            retrieve_top_k = 20

        rerank_top_n_raw = os.getenv("RERANKER_TOP_N") or "3"
        try:
            rerank_top_n = max(1, int(str(rerank_top_n_raw).strip()))
        except ValueError:
            rerank_top_n = 3

        # ---- Retrieval (backend split) -----------------------------------
        t_search = time.perf_counter()
        chunks: list[dict] = []  # list of {"content","sourcepage"} for reranker
        if _vector_search_backend() == "zilliz":
            from utility import zilliz_client as _zilliz_client

            hits = _zilliz_client.search_chunks(
                query_vector=vector,
                query_text=question,
                top_k=retrieve_top_k,
                category_ids=None,
            )
            for h in hits:
                sp = h.get("sourcepage") or h.get("source_file") or h.get("title") or ""
                ct = h.get("content") or h.get("text") or ""
                chunks.append({"sourcepage": str(sp), "content": str(ct)})
        else:
            # Azure AI Search path — keep BM25 hybrid (search_text + vector_queries)
            # but drop QueryType.SEMANTIC; the NIM reranker below handles re-ranking
            # uniformly across both backends.
            vector_query = VectorizedQuery(
                vector=vector, k_nearest_neighbors=retrieve_top_k, fields="contentVector"
            )
            results = search_client.search(
                search_text=question,
                vector_queries=[vector_query],
                filter=category_filter,
                top=retrieve_top_k,
            )
            for r in results:
                chunks.append(
                    {"sourcepage": r["sourcepage"], "content": r["content"]}
                )
        _last_extract_context_latencies["retrieval:vector_search_sec"] = round(
            time.perf_counter() - t_search, 3
        )

        # ---- NIM reranker (NVIDIA llama-nemotron-rerank-1b-v2) -----------
        t_rerank = time.perf_counter()
        # Honors ENABLE_RERANKER toggle and RERANKER_TOP_N in unified.env.
        # On any reranker failure, returns the original order trimmed to top_n.
        _bar = "=" * 72
        print(
            f"\n{_bar}\n"
            f">>> NIM-RERANKER :: CALL-SITE REACHED (inference.fetch_vector_context) <<<\n"
            f"{_bar}\n"
            f"about to call rerank_chunks(...)  input_chunks = {len(chunks)}\n"
            f"{_bar}\n",
            flush=True,
        )
        try:
            from utility.reranker import rerank_chunks

            final_chunks = rerank_chunks(question, chunks)
            print(
                f"\n{_bar}\n"
                f">>> NIM-RERANKER :: CALL-SITE RETURNED <<<\n"
                f"{_bar}\n"
                f"rerank_chunks returned {len(final_chunks)} chunks\n"
                f"{_bar}\n",
                flush=True,
            )
        except Exception as e:
            print(
                f"\n{_bar}\n"
                f">>> NIM-RERANKER :: CALL-SITE EXCEPTION <<<\n"
                f"{_bar}\n"
                f"error_type    = {type(e).__name__}\n"
                f"error_message = {e}\n"
                f"falling back to retrieval order, top-{rerank_top_n} of {len(chunks)}\n"
                f"{_bar}\n",
                flush=True,
            )
            final_chunks = chunks[:rerank_top_n]
        _last_extract_context_latencies["retrieval:rerank_sec"] = round(
            time.perf_counter() - t_rerank, 3
        )
        _last_extract_context_latencies["retrieval:vector_total_sec"] = round(
            time.perf_counter() - t_vec, 3
        )

        result_list = {"chunks": [], "sources": []}
        for c in final_chunks:
            sp = c.get("sourcepage") or ""
            ct = c.get("content") or ""
            result_list["sources"].append(sp)
            result_list["chunks"].append(f"{sp}: {ct}")
        return result_list
    
    async def fetch_graph_context():
        t_graph = time.perf_counter()
        # GraphRAG artifacts live under blob path ``graphragoutput/<category_id>/artifacts``.
        # Must match the category used at index time (same LanceDB vector dim as indexer).
        # Optional full override: GRAPH_RAG_ARTIFACTS_FOLDER=graphragoutput/<uuid>/artifacts
        print(
            "########################## graphrag_category #############################",
            graphrag_category,
        )
        BLOB_FOLDER_PATH = resolve_graph_artifacts_folder(graphrag_category)
        print("*************** BLOB_FOLDER_PATH ***************", BLOB_FOLDER_PATH)

        # First call: downloads 5 parquet files, connects LanceDB,
        # stores entity embeddings, builds ``LocalSearchMixedContext``.
        # Subsequent calls: instant cache hit, only ``build_context``
        # below runs per question.
        t_boot = time.perf_counter()
        Localcontext_builder = await asyncio.to_thread(
            _get_graph_context_builder, BLOB_CONTAINER_NAME, BLOB_FOLDER_PATH
        )
        _last_extract_context_latencies["retrieval:graph_bootstrap_sec"] = round(
            time.perf_counter() - t_boot, 3
        )

        try:
            t_build = time.perf_counter()
            context = await asyncio.to_thread(
                Localcontext_builder.build_context,
                question,
                top_k_mapped_entities=2,
                top_k_relationships=2,
                max_tokens=12_000,
            )
            _last_extract_context_latencies["retrieval:graph_build_context_sec"] = round(
                time.perf_counter() - t_build, 3
            )
        except ValueError as ve:
            msg = str(ve).lower()
            if "vector size" in msg and "does not match" in msg:
                print(
                    "\n[GraphRAG] Embedding dimension mismatch (query vs LanceDB index).\n"
                    "  Query embeddings use EMBEDDING_BACKEND / NVIDIA_EMBEDDING_MODEL "
                    "(e.g. nvidia/nv-embedqa-e5-v5 -> 1024 dims).\n"
                    "  This artifact folder was built with a different embedding width "
                    "(often 1536 for older Azure text-embedding-3-small indices).\n"
                    "  Fix: re-run GraphRAG indexing with ``python graphrag_index_runner.py`` "
                    "and data/settings.yaml NIM embeddings, then publish to this blob path; "
                    "or set GRAPH_RAG_EMBEDDING_BACKEND=azure only for legacy 1536-dim folders.\n"
                    f"  BLOB_FOLDER_PATH={BLOB_FOLDER_PATH}\n"
                    f"  Original error: {ve}\n",
                    flush=True,
                )
            raise
        print("graph_context :::::", context)
        _last_extract_context_latencies["retrieval:graph_total_sec"] = round(
            time.perf_counter() - t_graph, 3
        )
        return context

    # Fetch contexts based on selector
    result: dict = {}
    if selector == "vector":
        vector_context = await fetch_vector_context()
        result = {"vector_context": vector_context}

    elif selector == "graph":
        graph_context = await fetch_graph_context()
        result = {"graph_context": {"chunks": [str(graph_context)]}}

    elif selector == "hybrid":
        vector_context, graph_context = await asyncio.gather(
            fetch_vector_context(), fetch_graph_context()
        )
        result = {
            "vector_context": vector_context,
            "graph_context": {"chunks": [str(graph_context)]},
            "vector_weight": vector_weight,
            "graph_weight": graph_weight,
        }

    else:
        print("Invalid selector provided")
        return {}

    _last_extract_context_latencies["retrieval:extract_context_total_sec"] = round(
        time.perf_counter() - t_extract_start, 3
    )
    _last_extract_context_latencies["retrieval:search_mode"] = selector or "unknown"
    return result
    

 
def plot_to_base64(plot_code):
    try:
        # Set figure size before executing plot code
        plt.figure(figsize=(8, 6))  # Adjust the size as needed
       
        # Clean up the plot code if necessary
        plot_code = plot_code.replace("plt.show()", " ")  # Prevent plt.show() from blocking execution

        # Run generated code inside an explicit context so symbols like
        # pd/plt/sns/df resolve consistently during lambdas/comprehensions.
        exec_ctx = {
            "pd": pd,
            "plt": plt,
            "sns": sns,
        }
        try:
            exec(plot_code, exec_ctx, exec_ctx)
        except Exception as exec_err:
            # Common model bug: label lambda uses undefined index variable.
            # Drop that fragile line and rely on generic bar annotations.
            print(f"Plot code primary exec failed: {exec_err}. Retrying with safe label fallback.")
            safe_lines = []
            for line in plot_code.splitlines():
                stripped = line.strip()
                if ".apply(lambda" in stripped and "plt.text(" in stripped:
                    continue
                safe_lines.append(line)
            safe_code = "\n".join(safe_lines)
            plt.clf()
            plt.figure(figsize=(8, 6))
            exec(safe_code, exec_ctx, exec_ctx)

        # Generic value labels for bar plots if bars exist.
        ax = plt.gca()
        if getattr(ax, "patches", None):
            for patch in ax.patches:
                height = patch.get_height()
                if height is None:
                    continue
                try:
                    label = f"{float(height):,.0f}"
                except Exception:
                    label = str(height)
                ax.annotate(
                    label,
                    (patch.get_x() + patch.get_width() / 2.0, height),
                    ha="center",
                    va="bottom",
                    xytext=(0, 4),
                    textcoords="offset points",
                )
       
        # Ensure that the layout of the plot is not cropped
        plt.tight_layout()
 
        # Convert the plot to a base64-encoded image using 'bbox_inches="tight"' to avoid cropping
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)  # Use higher DPI for better resolution
        buf.seek(0)
       
        # Encode the plot as base64
        plot_base64 = base64.b64encode(buf.read()).decode('utf-8')
       
        # Close the plot
        plt.close()
       
        return plot_base64
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    
    
    
def parse_agent_content_json(content):
    """
    Parse JSON from an agent message. Handles markdown fences, leading/trailing prose,
    and models that wrap JSON in extra text (common with non-GPT models).
    Returns {} if nothing valid is found.
    """
    if content is None:
        return {}
    s = str(content).replace("```json", "").replace("```", "").strip()
    if not s:
        return {}
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Trying decoding the first JSON object found inside mixed text.
    decoder = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(s[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue

    # Resilient fallback for JSON-like messages with malformed string escaping.
    parsed = {}
    import re

    m = re.search(r'"analysis_type"\s*:\s*"([^"]+)"', s, re.DOTALL)
    if m:
        parsed["analysis_type"] = m.group(1).strip()

    m = re.search(r'"sql_critic_evaluation"\s*:\s*([01])', s, re.DOTALL)
    if m:
        parsed["sql_critic_evaluation"] = int(m.group(1))

    m = re.search(r'"sql_query"\s*:\s*(null|"[^"]*")', s, re.DOTALL)
    if m:
        raw = m.group(1).strip()
        parsed["sql_query"] = None if raw == "null" else raw.strip('"')

    for key in ("feedback", "sql_explanation", "sql_db_output"):
        m = re.search(
            rf'"{key}"\s*:\s*"(.*?)"\s*(?:,\s*"[a-zA-Z_]+"|\s*\}})',
            s,
            re.DOTALL,
        )
        if m:
            parsed[key] = m.group(1).strip()

    if parsed:
        return parsed

    print("parse_agent_content_json: could not parse JSON from agent message (preview):", s[:400])
    return {}


def parse_formatted_final_answer(llm_output: str, source_context: Any = None) -> dict[str, Any]:
    """
    Parse ``formating_final_answer`` LLM output into ``{"final_answer": [{type, text}, ...]}``.

    The formatter model often embeds user text with unescaped quotes, which breaks
    ``json.loads``. Fall back to the pre-format ``source_context`` (sql_answer / llm_answer).
    """
    parsed = parse_agent_content_json(llm_output)
    if isinstance(parsed, dict):
        fa = parsed.get("final_answer")
        if isinstance(fa, list) and fa:
            return parsed

    sql_t = ""
    llm_t = ""
    if isinstance(source_context, dict):
        sql_t = str(source_context.get("sql_answer") or "").strip()
        llm_t = str(source_context.get("llm_answer") or "").strip()

    parts: list[dict[str, str]] = []
    if sql_t:
        parts.append({"type": "sql", "text": sql_t})
    if llm_t:
        parts.append({"type": "llm", "text": llm_t})

    if not parts:
        raw = str(llm_output or "").strip()
        if raw:
            parts.append({"type": "llm", "text": raw})

    if parts:
        print(
            "[format_final_answer] JSON parse fallback: using source_context / raw text",
            flush=True,
        )
        return {"final_answer": parts}

    return {"final_answer": [{"type": "llm", "text": ""}]}


def build_generic_sql_fallback_answer(messages):
    """
    Generic fallback for SQL / Both-dependent flows.

    Does not hardcode business entities, product names, regions, columns, or use cases.
    It simply uses:
    1. successful Sql_tool outputs
    2. latest useful SQL agent explanation / feedback
    to create a non-empty final answer.
    """
    successful_outputs = []
    useful_texts = []
    latest_sql_query = ""

    for msg in messages:
        name = msg.get("name")
        content = str(msg.get("content") or "").strip()

        if not content:
            continue

        if name == "Sql_tool":
            if content.lower() in ("none", "[]"):
                continue
            if "An error occurred while execusting the query" in content:
                continue

            try:
                rows = json.loads(content)
                if isinstance(rows, list) and rows:
                    successful_outputs.append(rows)
            except Exception:
                successful_outputs.append(content)

        if name in ("Sql_Generator", "Sql_Execution_Critic", "Insight_Generator"):
            parsed = parse_agent_content_json(content)

            query = parsed.get("sql_query")
            if isinstance(query, str) and query.strip():
                latest_sql_query = query.strip()

            for key in (
                "sql_answer",
                "sql_explanation",
                "feedback",
                "Inference",
                "inference",
                "sql_db_output",
            ):
                value = parsed.get(key)

                if value is None:
                    continue

                if isinstance(value, (list, dict)):
                    useful_texts.append(json.dumps(value, ensure_ascii=False))
                    continue

                if isinstance(value, str) and value.strip():
                    low = value.lower()

                    # Ignore pure error messages as final answer text
                    if "incorrect syntax" in low:
                        continue
                    if "invalid column name" in low:
                        continue
                    if "error occurred" in low:
                        continue

                    useful_texts.append(value.strip())

    if not successful_outputs and not useful_texts:
        return {"sql_answer": "", "llm_answer": ""}

    sql_parts = []

    if successful_outputs:
        for idx, rows in enumerate(successful_outputs, start=1):
            if isinstance(rows, list):
                preview = json.dumps(rows, ensure_ascii=False)
            else:
                preview = str(rows)

            sql_parts.append(f"SQL result {idx}: {preview}")

    sql_answer = "\n".join(sql_parts)

    llm_answer = ""
    if useful_texts:
        # Use latest useful interpretation from the agents
        llm_answer = useful_texts[-1]

    if latest_sql_query and not sql_answer:
        sql_answer = f"Executed SQL query: {latest_sql_query}"

    return {
        "sql_answer": sql_answer,
        "llm_answer": llm_answer,
    }

def agent_output_jsonparser(chat_history, critic_agent):
    messages = chat_history.chat_history
    llm_answer_maker_data = [item for item in messages if item.get('name') == critic_agent]
    complete_messages = []
 
    for item in llm_answer_maker_data:
        # Extract and clean the content from each message
        last_message = item["content"].replace("Happy with the answer", "").strip().replace("```json", "").replace("```", "").strip()
       
        # Convert the cleaned message to a dictionary and append it to the list
        try:
            complete_messages.append(json.loads(last_message))
        except json.JSONDecodeError:
            print("Something went wrong with JSON decoding.")
 
 
    # Extracting the last message
    if complete_messages:  # Check if the list is not empty
        last_message = complete_messages[-1]
    else:
        last_message = None
 
    # Convert to a JSON string for the last message
    last_message_json = json.dumps(last_message, indent=4) if last_message else "No messages found."
    return last_message_json

 



async def start_agenting_process(query, index_type, filter, explain_code, category, email):
    if not query:
        return {}

    from utility.latency_trace import LatencyTrace
    from utility.unified_nat_orchestrator import run_unified_nat_orchestration

    workflow_start = time.time()
    prep = LatencyTrace()

    if not category:
        category = _clean_env_val(os.getenv("GRAPH_RAG_DEFAULT_CATEGORY_ID")) or None

    t0 = time.perf_counter()
    user_seleted_tables = get_tables_list_by_email(email)
    prep.record("Load user SQL table list", time.perf_counter() - t0)

    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& all_table_schemas &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&', user_seleted_tables)

    selected_tables = []
    current_engine = _ensure_engine()
    if isinstance(user_seleted_tables, dict):
        selected_tables = user_seleted_tables.get('tables_list') or []

    if not selected_tables:
        t_list = time.perf_counter()
        if current_engine is not None:
            selected_tables = inspect(current_engine).get_table_names(schema=category_name)
            if not selected_tables:
                selected_tables = inspect(current_engine).get_table_names()
        prep.record("List tables from SQL engine", time.perf_counter() - t_list)

    t_schema = time.perf_counter()
    all_table_schemas = get_sql_table_schema(connection_string, selected_tables)
    prep.record("Load SQL table schemas", time.perf_counter() - t_schema)

    if (
        not all_table_schemas
        or (isinstance(all_table_schemas, dict) and len(all_table_schemas) == 0)
        or (isinstance(all_table_schemas, str) and all_table_schemas.lower().startswith('error'))
    ):
        t_fb = time.perf_counter()
        if current_engine is not None:
            all_table_schemas = get_schema_tables(current_engine, category_name)
        prep.record("SQL schema fallback (category tables)", time.perf_counter() - t_fb)

    if not all_table_schemas:
        t_cross = time.perf_counter()
        try:
            if current_engine is None:
                raise RuntimeError('SQL engine unavailable')
            inspector = inspect(current_engine)
            all_schema_dict = {}
            for schema_name in inspector.get_schema_names():
                if not schema_name or schema_name.startswith('db_'):
                    continue
                table_names = inspector.get_table_names(schema=schema_name)
                for tbl in table_names:
                    try:
                        cols = inspector.get_columns(tbl, schema=schema_name)
                        all_schema_dict[f'{schema_name}.{tbl}'] = {
                            col['name']: str(col['type']) for col in cols
                        }
                    except Exception:
                        continue
            if all_schema_dict:
                all_table_schemas = all_schema_dict
        except Exception as schema_exc:
            print('Cross-schema introspection fallback failed:', schema_exc)
        prep.record("SQL cross-schema introspection", time.perf_counter() - t_cross)

    print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& all_table_schemas &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&', all_table_schemas)

    print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ index_type ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^', index_type)

    return await run_unified_nat_orchestration(
        query=query,
        index_type=index_type,
        filter_value=filter,
        explain_code=explain_code,
        category=category,
        email=email,
        all_table_schemas=all_table_schemas,
        connection_string=connection_string,
        prep_steps=prep.to_list(),
        workflow_start=workflow_start,
    )
