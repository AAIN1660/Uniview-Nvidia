from pathlib import Path

from fastapi import FastAPI, HTTPException
import logging
import os
from datetime import datetime
import time
import threading
import uuid
from azure.cosmos import CosmosClient, exceptions
from azure.cosmos.errors import CosmosHttpResponseError
from dotenv import load_dotenv
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from utility.blob_storage import get_blob_service_client, sync_directory_to_bucket
from difflib import SequenceMatcher
import re
import bcrypt
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
import urllib
import yaml
import shutil
import subprocess
import sys
import tempfile
import json
from azure.storage.queue import QueueClient
from tenacity import retry, wait_random_exponential, stop_after_attempt
import PyPDF2
from utility.nim_chat_client import chat_completion_sync

load_dotenv("unified.env")

AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX_NAME")
AZURE_QNA_INDEX = os.getenv("AZURE_QA_INDEX_NAME")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_OPENAI_SERVICE_BASE = os.getenv("AZURE_OPENAI_API_BASE")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_TYPE = os.getenv("OPENAI_API_TYPE")
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME")
AZURE_OPENAI_CHATGPT_MODEL = os.getenv("GPT3_LLM_MODEL_NAME")
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
KB_FIELDS_CONTENT = "content"
KB_FIELDS_SOURCEPAGE = "sourcepage"

azure_search_credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)

def _strip_quotes(v):
    if v is None:
        return None
    v = str(v).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        v = v[1:-1].strip()
    return v


COSMOS_DATABASE_NAME = _strip_quotes(os.environ["COSMOS_DATABASE_NAME"])
COSMOS_ENDPOINT = _strip_quotes(os.environ["COSMOS_ENDPOINT"])
COSMOS_KEY = _strip_quotes(os.environ["COSMOS_KEY"])
COSMOS_UPLOAD_CONTAINER = _strip_quotes(os.environ["UPLOAD_CONTAINER_NAME"])


# -----------------------------------------------------------------------------
# Metadata document store backend selector.
#
# METADATA_BACKEND=mongo   ->  local MongoDB Community Edition (active default,
#                              NVIDIA-blueprint NoSQL alternative to Cosmos DB)
# METADATA_BACKEND=cosmos  ->  Azure Cosmos DB (legacy; preserved for rollback)
#
# Same backend-flag pattern as VECTOR_SEARCH_BACKEND.  All callers below get
# the SAME container API regardless of backend, because mongo_document_store
# exposes a Cosmos-API-compatible wrapper (read_item / query_items /
# upsert_item / replace_item / delete_item / read_all_items).
# -----------------------------------------------------------------------------
def _load_metadata_db():
    backend = (os.getenv("METADATA_BACKEND") or "cosmos").strip().strip('"').strip("'").lower()
    if backend == "mongo":
        from utility.mongo_document_store import get_database as _get_mongo_db
        print(f"[metadata-db] backend=mongo db={os.getenv('MONGO_DATABASE_NAME')}")
        return _get_mongo_db(COSMOS_DATABASE_NAME)
    print(f"[metadata-db] backend=cosmos db={COSMOS_DATABASE_NAME}")
    return CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY).get_database_client(
        COSMOS_DATABASE_NAME
    )


database = _load_metadata_db()
# Legacy Cosmos init (kept for rollback reference):
# client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
# database = client.get_database_client(COSMOS_DATABASE_NAME)
tran_container = database.get_container_client("transactions")
user_container = database.get_container_client("gi_users")
config_container = database.get_container_client("config")
category_container = database.get_container_client("gi_category")
feedback_container = database.get_container_client("gi_qa")
upload_container = database.get_container_client(COSMOS_UPLOAD_CONTAINER)


container_name = os.getenv("BLOB_STORAGE_CONTAINER_NAME")

blob_service_client = get_blob_service_client()
container_client = blob_service_client.get_container_client(container_name)

QUEUE_NAME = os.getenv("AZURE_QUEUE_STORAGE_NAME")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
QUEUE_CLIENT = QueueClient.from_connection_string(
    AZURE_STORAGE_CONNECTION_STRING, QUEUE_NAME
)


async def insert_qa_records(
    query,
    answer,
    start_time,
    thoughts,
    data_points,
    include_category,
    token_usage,
    email,
    credit_used,
):
    # container = current_app.config['cosmos_db'].get_container_client("gi_qa")
    end_time = time.time()
    ex_time = end_time - start_time
    qa_id = uuid.uuid4()
    item = {
        "id": str(qa_id),
        "question": query,
        "answer": answer,
        "include_category": include_category,
        "feedback": "",
        "createdBy": email,
        "createdAt": str(datetime.now()),
        "updatedAt": "",
        "updatedBy": "",
        "ex_time": ex_time,
        "thoughts": thoughts,
        "data_points": data_points,
        "token_usage": token_usage,
        "credit_used": credit_used,
    }
    feedback_container.create_item(body=item)
    return item


def calculate_balance(email):
    # Fetching data from Cosmos DB transactions table
    # container_transactions = current_app.config['cosmos_db'].get_container_client("transactions")
    start_time_check_balance_query = datetime.now()
    query = f"SELECT * FROM transactions t WHERE t.email = '{email}' ORDER BY t.transaction_ts DESC"
    cosmos_transactions = tran_container.query_items(
        query=query, enable_cross_partition_query=True
    )
    end_time_check_balance_query = datetime.now()
    time_taken_check_balance_query = (
        end_time_check_balance_query - start_time_check_balance_query
    ).total_seconds()
    print("time_taken_check_balance_query", time_taken_check_balance_query)
    transactions = list(cosmos_transactions)
    # print('calculate_transactions', transactions)

    start_time_check_balance_logicrun = datetime.now()

    # Processing Cosmos transactions
    user_credits = [transaction.get("credit", 0) for transaction in transactions]
    sum_debit = sum(transaction.get("debit", 0) for transaction in transactions)

    # Calculating balance
    balance = sum(user_credits) - sum_debit
    print("calculate_balance", balance)
    logging.info(f"balance : {balance}")
    roundbalance = round(balance, 2)
    print("calculate_round_balance", roundbalance)
    logging.info(f"roundbalance : {roundbalance}")
    end_time_check_balance_logicrun = datetime.now()
    time_taken_check_balance_logicrun = (
        end_time_check_balance_logicrun - start_time_check_balance_logicrun
    ).total_seconds()
    print("time_taken_check_balance_logicrun", time_taken_check_balance_logicrun)
    return roundbalance


async def calculate_balance2(email):
    # Fetching data from Cosmos DB transactions table
    # container_transactions = current_app.config['cosmos_db'].get_container_client("transactions")
    query = f"SELECT * FROM transactions t WHERE t.email = '{email}' ORDER BY t.transaction_ts DESC"
    cosmos_transactions = tran_container.query_items(
        query=query, enable_cross_partition_query=True
    )

    transactions = list(cosmos_transactions)
    # print('calculate_transactions2', transactions)

    # Processing Cosmos transactions
    user_credits = [transaction.get("credit", 0) for transaction in transactions]
    sum_debit = sum(transaction.get("debit", 0) for transaction in transactions)

    # Calculating balance
    balance = sum(user_credits) - sum_debit
    print("calculate_balance2", balance)
    logging.info(f"balance : {balance}")
    roundbalance = round(balance, 2)
    print("calculate_round_balance2", roundbalance)
    logging.info(f"roundbalance : {roundbalance}")
    return roundbalance


async def update_transactions_table(
    email, balance, service_type, token_usage=None, credit_used=0, credit_assigned=0
):
    if service_type == "expired":
        transaction_type = 2
    else:
        transaction_type = 1

    # tran = current_app.config['cosmos_db'].get_container_client("transactions")

    try:
        current_trans_id = get_current_trans_id_from_database()
        print(f"current_trans_id: {current_trans_id}")
        current_utc_datetime = datetime.utcnow()
        formatted_datetime = current_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
        # Add a new entry to transactions table with zero balance for the new user
        new_transaction = {
            "surr_no": current_trans_id + 1,
            "id": str(uuid.uuid1()),
            "email": email,
            "credit": credit_assigned,
            "balance": balance,
            "debit": credit_used,
            "purchase_type": 1,
            "service_type": service_type,
            "transaction_type": transaction_type,  # Assuming 1 represents a user creation transaction
            "transaction_ts": formatted_datetime,
        }
        # Include "token_usage" only if it's provided
        if credit_assigned != 0:
            new_transaction["credit"] = credit_assigned
        if token_usage is not None:
            new_transaction["token_usage"] = token_usage
        if credit_used != 0:
            new_transaction["debit"] = credit_used
        tran_container.create_item(body=new_transaction)

        # Fetch user's role and latest credit balance
        user_info = get_user_info(email)
        return {
            "message": "Transaction updated successfully",
            "role": user_info["role"],
            "balance": user_info["balance"],
        }

    except exceptions.CosmosHttpResponseError as cosmos_error:
        print(f"Error updating transactions table: {cosmos_error}")
        return {"message": f"Error updating transactions table: {cosmos_error}"}
    except Exception as e:
        print(f"Error updating transactions table: {str(e)}")
        return {"message": f"Error updating transactions table: {str(e)}"}


def get_current_trans_id_from_database():
    # container_transactions = current_app.config['cosmos_db'].get_container_client("transactions")
    query = "SELECT TOP 1 c.surr_no FROM c ORDER BY c.surr_no DESC"
    result = tran_container.query_items(query=query, enable_cross_partition_query=True)
    try:
        last_trans_id = next(result)
        return last_trans_id["surr_no"]
    except StopIteration:
        return 0
    except CosmosHttpResponseError as cosmos_error:
        print(f"Error querying Cosmos DB for transaction ID: {cosmos_error}")
        return 0


def get_user_info(email):
    # container_users = current_app.config['cosmos_db'].get_container_client("gi_users")
    query = (
        f"SELECT TOP 1 c.role, c.id FROM c WHERE c.email = '{email}' ORDER BY c.id DESC"
    )
    result = user_container.query_items(query=query, enable_cross_partition_query=True)

    try:
        user_info = next(result)
        return {"role": user_info["role"], "balance": calculate_balance(email)}
    except StopIteration:
        return {"role": None, "balance": 0}
    except CosmosHttpResponseError as cosmos_error:
        print(f"Error querying Cosmos DB for user info: {cosmos_error}")
        return {"role": None, "balance": 0}


def get_user_data():
    # user_container = current_app.config['cosmos_db'].get_container_client("gi_users")
    query = "SELECT * FROM c"
    result = user_container.query_items(query, enable_cross_partition_query=True)
    # print("resultttt:",result)
    return result


def get_transaction_data():
    # transaction_container = current_app.config['cosmos_db'].get_container_client("transactions")
    query = "SELECT * FROM c"
    result = tran_container.query_items(query, enable_cross_partition_query=True)
    return result


def check_balance(email):
    balance = calculate_balance(email)
    print("Balance", balance)
    if balance > 0:
        # Continue with the remaining code
        return True
    else:
        # Insufficient balance, return a message
        return False


async def get_inactive_categories():
    # container_users = current_app.config['cosmos_db'].get_container_client("gi_category")
    query = f"SELECT * FROM cat WHERE cat.status = 0"
    cat_list = list(
        category_container.query_items(query, enable_cross_partition_query=True)
    )
    # print("cat list to add in exclude category list:", cat_list)
    return cat_list


async def get_active_categories():
    # container_users = current_app.config['cosmos_db'].get_container_client("gi_category")
    query = f"SELECT * FROM cat WHERE cat.status = 1"
    cat_list = list(
        category_container.query_items(query, enable_cross_partition_query=True)
    )
    return cat_list


async def credit_used_by_query(token_usage):
    print("token_usage", token_usage)
    try:
        config_data = []
        user_query = f"SELECT * FROM c WHERE c.id = 'configuration'"
        config_data = list(
            config_container.query_items(
                query=user_query, enable_cross_partition_query=True
            )
        )
        print('config_data[0]["tokens_per_credit"]', config_data[0]["tokens_per_credit"])
        credit_used = float(
            round(int(token_usage) / float(config_data[0]["tokens_per_credit"]), 1)
        )
        print(credit_used, credit_used)
        
        return credit_used
    except (ValueError, TypeError):
        print("Error: token_usage is not a valid integer")
        return 0.0


async def get_all_categories():
    # container_users = current_app.config['cosmos_db'].get_container_client("gi_category")
    query = f"SELECT * FROM cat"
    cat_list = list(
        category_container.query_items(query, enable_cross_partition_query=True)
    )
    # print("cat list to add all category list:", cat_list)
    return cat_list


def nonewlines(s: str) -> str:
    return s.replace("\n", " ").replace("\r", " ")


def list_blob_files():

    blob_service_client = get_blob_service_client()

    # Get the container client
    container_client = blob_service_client.get_container_client(container_name)

    # List blob names in the container
    blob_names = [blob.name for blob in container_client.list_blobs()]

    # print('blob_names', blob_names)

    return blob_names


# Function to calculate similarity
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def encrypt_password(password: str) -> str:
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed_password.decode()


def get_cosmos_client():
    return CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)


def get_database(client):
    return client.get_database_client(COSMOS_DATABASE_NAME)


def get_config_container():
    client = get_cosmos_client()
    database = get_database(client)
    return database.get_container_client(config_container)


# Step 2: Fetch tables from the specified schema dynamically
# ---------------------------------------------------------------------------
# Pooled SQLAlchemy engine cache
# ---------------------------------------------------------------------------
# One engine (with its own connection pool) per connection string, shared
# process-wide. Avoids the per-call ``create_engine(...)`` cost in
# ``execute_sql_tool`` (invoked up to 8x per request inside the SQL critic
# loop) and the duplicate engine spun up by ``get_sql_table_schema`` on every
# request.

_sql_engine_cache: dict[str, Engine] = {}
_sql_engine_lock = threading.Lock()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return default


def get_sql_engine(connection_string: str) -> Engine:
    """Return a shared, pooled SQLAlchemy engine for ``connection_string``.

    Pool tunables via env:
      - ``SQL_POOL_SIZE`` (default 5)
      - ``SQL_MAX_OVERFLOW`` (default 10)
      - ``SQL_POOL_RECYCLE`` (default 1800 seconds)
      - ``SQL_POOL_PRE_PING`` (default True)
    """
    with _sql_engine_lock:
        eng = _sql_engine_cache.get(connection_string)
        if eng is not None:
            return eng
        eng = create_engine(
            connection_string,
            pool_size=_int_env("SQL_POOL_SIZE", 5),
            max_overflow=_int_env("SQL_MAX_OVERFLOW", 10),
            pool_recycle=_int_env("SQL_POOL_RECYCLE", 1800),
            pool_pre_ping=_bool_env("SQL_POOL_PRE_PING", True),
            future=True,
        )
        _sql_engine_cache[connection_string] = eng
        return eng


# ---------------------------------------------------------------------------
# Schema cache for ``get_sql_table_schema``
# ---------------------------------------------------------------------------
# Inspecting the DB on every ``start_agenting_process`` call is expensive
# (round trip + metadata reflection). Cache results by
# ``(connection_string, frozenset(table_names))`` with a TTL.

_sql_schema_cache: dict[tuple[str, frozenset], dict[str, object]] = {}
_sql_schema_lock = threading.Lock()
_SQL_SCHEMA_TTL_SEC = float(_int_env("SQL_SCHEMA_CACHE_TTL_SEC", 300))


def invalidate_sql_schema_cache(connection_string: str | None = None) -> None:
    """Drop cached SQL schemas.

    No-arg call clears the entire cache; pass a ``connection_string`` to
    drop only entries for that database. Call from your DB-connection
    update / table-selection update endpoints when the schema or
    selected tables actually change.
    """
    with _sql_schema_lock:
        if connection_string is None:
            _sql_schema_cache.clear()
            return
        for key in [k for k in _sql_schema_cache if k[0] == connection_string]:
            _sql_schema_cache.pop(key, None)


def get_sql_table_schema(connection_string, table_names):
    """
    Fetches the schema of multiple tables from the SQL Server database.

    Uses a shared pooled engine and an in-process cache keyed by
    ``(connection_string, frozenset(table_names))`` with a TTL controlled
    by env ``SQL_SCHEMA_CACHE_TTL_SEC`` (default 300s).

    :param connection_string: SQLAlchemy-style connection string
    :param table_names: Iterable of table names whose schemas are required
    :return: Dict with table names as keys and their schema details as values
    """
    try:
        key = (connection_string, frozenset(table_names or []))
    except TypeError:
        key = None

    if key is not None:
        now = time.time()
        with _sql_schema_lock:
            entry = _sql_schema_cache.get(key)
            if entry is not None:
                if _SQL_SCHEMA_TTL_SEC <= 0 or (now - float(entry["ts"])) < _SQL_SCHEMA_TTL_SEC:
                    return entry["value"]

    engine = get_sql_engine(connection_string)
    schema_dict: dict[str, object] = {}
    try:
        inspector = inspect(engine)
        available_tables = inspector.get_table_names()

        for table_name in table_names:
            if table_name in available_tables:
                columns = inspector.get_columns(table_name)
                schema_dict[table_name] = {col['name']: str(col['type']) for col in columns}
            else:
                schema_dict[table_name] = f"Table '{table_name}' does not exist."
    except Exception as e:
        return f"Error fetching schema: {e}"

    if key is not None:
        with _sql_schema_lock:
            _sql_schema_cache[key] = {"value": schema_dict, "ts": time.time()}

    return schema_dict


def _vector_search_backend() -> str:
    b = (os.getenv("VECTOR_SEARCH_BACKEND") or "azure").strip().lower()
    return "zilliz" if b in ("zilliz", "milvus") else "azure"


def handle_vector_upload(file_path, file_name, file_id, email):
    """
    Upload PDF to blob storage and ingest into the active vector backend.
    Returns a list of chunk IDs created in the vector store (empty for Azure queue path).
    """
    print("file_path:", file_path)
    blob_name = os.path.basename(file_path)
    blob_client = container_client.get_blob_client(blob_name)
    print("blob_name:", blob_name)

    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)

    chunk_ids: list[str] = []

    if _vector_search_backend() == "zilliz":
        from utility.zilliz_ingestion import ingest_pdf_bytes_to_zilliz

        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        result = ingest_pdf_bytes_to_zilliz(
            pdf_bytes, source_name=file_name
        )
        chunk_ids = result.get("ids", [])
        print(f"[Zilliz] Ingested {result.get('chunks', 0)} chunks for {file_name}")
    else:
        msg = json.dumps(
            {"file_name": file_name, "file_id": str(file_id), "email": email}
        )
        QUEUE_CLIENT.send_message(msg)

    return chunk_ids


def load_settings(file_path: str, category_id) -> dict:
    """
    Load settings from a YAML file.

    Args:
        file_path (str): Path to the YAML settings file.

    Returns:
        dict: Parsed settings as a dictionary.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Settings file not found: {file_path}")

    # Load the settings.yaml file
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)

    output_blob_folder_path = f"graphragoutput/{category_id}/artifacts"
    config["storage"]["base_dir"] = output_blob_folder_path

    report_blob_folder_path = f"graphragoutput/{category_id}/reports"
    config["reporting"]["base_dir"] = report_blob_folder_path

    # GraphRAG indexes on local disk; artifacts sync to MinIO after index.
    for section in ("input", "storage", "reporting"):
        if section in config and isinstance(config[section], dict):
            config[section]["type"] = "file"
            config[section].pop("connection_string", None)
            config[section].pop("container_name", None)

    # Save the updated settings back to the file
    with open(file_path, "w") as file:
        yaml.safe_dump(config, file)

        return config


async def run_graphrag_index(file_name, data_dir: str, category_id, graph_rag_files):
    print("$$$$$ GRAPH RAG INDEXING STARTED $$$$$$")

    print("@@@@ graph_rag_files @@@@", graph_rag_files)

    SETTINGS_FILE = os.path.join(os.getcwd(), "data", "settings.yaml")
    config = load_settings(SETTINGS_FILE, category_id)

    if not os.path.isdir(data_dir):
        raise HTTPException(
            status_code=400, detail=f"Invalid data directory: {data_dir}"
        )

    try:
        backend_root = Path(__file__).resolve().parent.parent
        runner = backend_root / "graphrag_index_runner.py"
        subprocess.run(
            [sys.executable, str(runner), "--root", data_dir],
            check=True,
            cwd=str(backend_root),
        )

        bucket = _strip_quotes(os.getenv("BLOB_STORAGE_CONTAINER_NAME"))
        artifacts_local = os.path.join(
            backend_root, f"graphragoutput/{category_id}/artifacts"
        )
        reports_local = os.path.join(
            backend_root, f"graphragoutput/{category_id}/reports"
        )
        if bucket and os.path.isdir(artifacts_local):
            n = sync_directory_to_bucket(
                artifacts_local,
                bucket,
                f"graphragoutput/{category_id}/artifacts",
            )
            print(f"[blob-storage] synced {n} artifact file(s) to MinIO")
        if bucket and os.path.isdir(reports_local):
            n = sync_directory_to_bucket(
                reports_local,
                bucket,
                f"graphragoutput/{category_id}/reports",
            )
            print(f"[blob-storage] synced {n} report file(s) to MinIO")

        for file_info in graph_rag_files:
            file_name = file_info.get("file_name")
            file_path = file_info.get("file_path")

            blob_name = file_name
            query = "SELECT * FROM gi_uploads r WHERE r.file_name = @blob_name"
            query_params = [{"name": "@blob_name", "value": blob_name}]

            # Execute the parameterized query
            try:
                query_result = list(
                    upload_container.query_items(
                        query=query,
                        parameters=query_params,
                        enable_cross_partition_query=True,
                    )
                )
            except Exception as e:
                logging.error(f"Error querying database: {e}")
                raise HTTPException(
                    status_code=500, detail="Error querying the database."
                )

            if not query_result:
                raise HTTPException(
                    status_code=404,
                    detail=f"No record found for file_name: {blob_name}",
                )

            # Retrieve the first item (assuming unique file_name)
            file_item = query_result[0]
            logging.info(f"File_item fetched: {file_item}")

            # Update the graphrag_index_status
            file_item["graphrag_index_status"] = 1

            response = upload_container.replace_item(
                item=file_item["id"], body=file_item
            )
            logging.info(f"Database updated successfully: {response}")

        print("$$$$$ GRAPH RAG INDEXING COMPLETED $$$$$$")
        logging.info("End of the Graph Rag indexing function.")

        try:
            from utility.graphrag_artifacts import graph_lancedb_uri
            from utility.inference import invalidate_graph_context_cache

            folder = f"graphragoutput/{category_id}/artifacts"
            container = os.getenv("BLOB_STORAGE_CONTAINER_NAME")
            if container:
                invalidate_graph_context_cache(container, folder)
            lance_path = graph_lancedb_uri(folder)
            if os.path.isdir(lance_path):
                shutil.rmtree(lance_path, ignore_errors=True)
                print(f"[GraphRAG] cleared local LanceDB cache: {lance_path}")
        except Exception as cache_exc:
            logging.warning("GraphRAG post-index cache clear skipped: %s", cache_exc)

        return {"status": "success", "message": "Graph Indexing completed"}

    except subprocess.CalledProcessError as e:
        logging.error(f"Indexing process failed with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Indexing process failed with return code {e.returncode}",
        )


def download_blob(container_name, blob_name, download_file_path):
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        with open(download_file_path, "wb") as download_file:
            download_file.write(blob_client.download_blob().readall())
        print(f"Downloaded blob {blob_name} to {download_file_path}")
    except Exception as e:
        print(f"Error downloading blob {blob_name}: {e}")


def upload_blob(container_name, blob_name, upload_file_path):
    try:
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        with open(upload_file_path, "rb") as upload_file:
            blob_client.upload_blob(upload_file, overwrite=True)
        print(f"Uploaded file {upload_file_path} to blob {blob_name}")
    except Exception as e:
        print(f"Error uploading blob {blob_name}: {e}")


def convert_pdf_to_text(pdf_file_path):
    try:
        with open(pdf_file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in range(len(reader.pages)):
                text += reader.pages[page].extract_text()
            return text
    except Exception as e:
        print(f"Error reading {pdf_file_path}: {e}")
        return None


def save_text_to_file(text, output_file_path):
    try:
        with open(output_file_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)
        print(f"Saved text to {output_file_path}")
    except Exception as e:
        print(f"Error saving text to {output_file_path}: {e}")


def process_pdf_blob(source_blob):
    # Configuration
    download_path = os.path.join(os.getcwd(), "data", "temp_downloaded.pdf")

    # Get the input file name without extension
    input_file_name = os.path.splitext(os.path.basename(source_blob))[0]

    # Set the destination text file path in blob
    destination_blob = f"graphraginput/input/{input_file_name}.txt"
    text_file_path = f"{input_file_name}.txt"

    # Step 1: Download the PDF file from the blob
    download_blob(container_name, source_blob, download_path)

    # Step 2: Convert the PDF to text
    text = convert_pdf_to_text(download_path)

    if text:
        # Step 3: Save the text to a file
        save_text_to_file(text, text_file_path)

        # Step 4: Upload the text file to the specified blob location
        upload_blob(container_name, destination_blob, text_file_path)

        # Cleanup temporary files
        os.remove(download_path)
        os.remove(text_file_path)


async def startGraphRagIndexing(file_name, directory, category_id, graph_rag_files):
    # try:
    print("file_name", file_name)
    # process_pdf_blob(file_name)
    response = await run_graphrag_index(
        file_name, directory, category_id, graph_rag_files
    )
    print("response", response)


# except Exception as e:
# 	logging.info(f"Error in graph rag generate embeddings function" )


async def process_query_and_update(
    email, query, token_usage, askResponse, start_time, include_category=None
):
    """
    Helper function to process a query, update balances, and log QA records.

    Parameters:
        email (str): User's email.
        query (str): User's query.
        token_usage (int): Token usage for the query.
        askResponse (dict): Response object with keys 'answer', 'thoughts', and 'data_points'.
        start_time (datetime): Start time of the query processing.
        include_category (str, optional): Categories to include.

    Returns:
        dict: Updated askResponse with 'uid' and 'balance'.
    """
    # Calculate credits used
    credit_used = await credit_used_by_query(token_usage)
    
    print('credit_used', credit_used)

    # Calculate balance
    balance = round(calculate_balance(email) - credit_used, 2)
    
    print('balance', balance)
    

    # Update transactions
    await update_transactions_table(
        email=email,
        balance=balance,
        service_type="Query",
        token_usage=token_usage,
        credit_used=credit_used,
    )

    # Insert QA record
    qa_record = await insert_qa_records(
        query=query,
        answer=askResponse["answer"],
        start_time=start_time,
        thoughts=askResponse["thoughts"],
        data_points=askResponse["data_points"],
        include_category=include_category,
        token_usage=token_usage,
        email=email,
        credit_used=credit_used,
    )

    # Update askResponse
    askResponse["uid"] = str(qa_record["id"])
    askResponse["balance"] = balance

    return askResponse


def get_tables_list_by_email(email: str):
    # Fetch user details
    user_query = f"SELECT * FROM c WHERE c.email = '{email}'"
    user_items = list(user_container.query_items(query=user_query, enable_cross_partition_query=True))
    
    if not user_items:
        return {"email": email, "tables_list": [], "selected_database": ""}
    
    user = user_items[0]
    
    selectedTables = user.get('tables_list', []) or []
    
    selectedDatabase = user.get('db_connection_id', "") or ""
    
        
    print('tables', type(selectedTables)) 
    
    print('tables', selectedTables)   
      
    
    return {"email": email, "tables_list": selectedTables, 'selected_database': selectedDatabase}



def formating_final_answer(context):
    template = """
    Expert Final Answer Maker
    Input:
    You will receive two inputs:
    SQL Answer -" A response generated from an SQL query.
    LLM Answer -" A response generated by a language model.
    Here is the Context : {context}
    
    Task:
    As an expert final answer maker, your goal is to combine both the SQL Answer and LLM Answer into a well-structured final response.
    Ensure the final answer is clear, concise, and free of duplication or repetition.
    Maintain a natural and logical flow while integrating insights from both sources.
    Use placeholders to allow color coding in the front end, distinguishing between the SQL-generated answer and the LLM-generated answer.
    Output Format:
    Return the response in the strictly mentioned JSON format with separate fields for SQL and LLM answers.
    Ensure a structured, readable, and meaningful integration of both answers.
    
    Strictly Maintain this below Example Output (JSON Format) don't give any addtional text in the ouput just follow below JSON format structure otput:
    {{"final_answer": [{{"type": "sql","text": "The total sales revenue for Q1 2024 is $1.2 million."}},{{"type": "llm","text": "This indicates a 15% increase compared to the previous quarter, suggesting strong market growth."}}] }}

    """
    prompt = template.format(context=context)
    print('###### prompt ###########', prompt)
    answer = chat_completion_sync(
        system="You are a helpful assistant.",
        user=prompt,
        temperature=0.0,
        max_tokens=1024,
    )
    print('***************** NIM llm call (format_answer) ********************')
    # print("chunk_ids :", chunk_ids)
    # print(f"Question: {query}\n")
    # print(f"Answer: {answer}\n")
    return answer
    # print(f"Context chunks:\n {chunk_content}")
 


