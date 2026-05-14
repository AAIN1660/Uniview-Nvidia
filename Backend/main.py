import uvicorn
import os
import json
import httpx
import logging
import aiohttp
import openai
import ast
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services import userCreditService, documentService, setupService
from routers import categoryManagementRouter, userManagementRouter, dbConnectionRouter, configManagementRouter, uploadManagementRouter
from dotenv import load_dotenv
from azure.cosmos import CosmosClient
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from utility.helper import *
from utility.acsServiceHelper import get_similar_qa
from utility.acsServiceHelper import qna_indexing
from utility.guardrails import check_input, check_output
from PyPDF2 import PdfReader, PdfWriter
import fitz
import re
import datetime
from urllib.parse import unquote_plus
from azure.storage.blob import BlobServiceClient
import io
import asyncio
import time
from contextlib import asynccontextmanager
from utility.inference import *


load_dotenv("unified.env")


def _clean_env(value, default=None):
    value = value if value is not None else default
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


# NAT-only mode: always route generation through NeMo Agent Toolkit workflow.
USE_NAT_WORKFLOW = True
NAT_WORKFLOW_URL = _clean_env(os.getenv("NAT_WORKFLOW_URL"), "http://127.0.0.1:8090/generate")
NAT_WORKFLOW_TIMEOUT_SEC = float(_clean_env(os.getenv("NAT_WORKFLOW_TIMEOUT_SEC"), "720"))

# Set logging level to ERROR or CRITICAL
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)
logging.getLogger('azure.monitor.opentelemetry.exporter.export._base').setLevel(logging.ERROR)

AZURE_SEARCH_SERVICE_ENDPOINT   = _clean_env(os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT"))
AZURE_SEARCH_INDEX               = _clean_env(os.getenv("AZURE_SEARCH_INDEX_NAME"))
AZURE_QNA_INDEX                  = _clean_env(os.getenv("AZURE_QA_INDEX_NAME"))
AZURE_SHARE_POINT_INDEXR_NAME    = _clean_env(os.getenv("AZURE_SHARE_POINT_INDEXR_NAME"))
AZURE_SHARE_POINT_INDEXES_NAME   = _clean_env(os.getenv("AZURE_SHARE_POINT_INDEXES_NAME"))
AZURE_SEARCH_ADMIN_KEY           = _clean_env(os.getenv("AZURE_SEARCH_ADMIN_KEY"))
AZURE_OPENAI_SERVICE_BASE        = _clean_env(os.getenv("AZURE_OPENAI_API_BASE"))
AZURE_OPENAI_VERSION             = _clean_env(os.getenv("AZURE_OPENAI_API_VERSION"))
AZURE_OPENAI_TYPE                = _clean_env(os.getenv("OPENAI_API_TYPE"))
AZURE_OPENAI_CHATGPT_DEPLOYMENT  = _clean_env(os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME"))
AZURE_OPENAI_CHATGPT_MODEL       = _clean_env(os.getenv("GPT3_LLM_MODEL_NAME"))
AZURE_OPENAI_EMB_DEPLOYMENT      = _clean_env(os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL"))
AZURE_OPENAI_KEY                 = _clean_env(os.getenv("AZURE_OPENAI_API_KEY"))
KB_FIELDS_CONTENT                = 'content'
KB_FIELDS_SOURCEPAGE             = 'sourcepage'

COSMOS_DATABASE_NAME = _clean_env(os.getenv("COSMOS_DATABASE_NAME"))
COSMOS_ENDPOINT      = _clean_env(os.getenv("COSMOS_ENDPOINT"))
COSMOS_KEY           = _clean_env(os.getenv("COSMOS_KEY"))
TOKEN_PER_CREDIT     = _clean_env(os.getenv("TOKEN_PER_CREDIT"))

# -----------------------------------------------------------------------------
# Metadata document store backend selector  (METADATA_BACKEND=mongo|cosmos).
# Same backend-flag pattern as VECTOR_SEARCH_BACKEND; the MongoDB wrapper
# exposes a Cosmos-API-compatible surface so callers below stay unchanged.
# -----------------------------------------------------------------------------
_METADATA_BACKEND = (_clean_env(os.getenv("METADATA_BACKEND")) or "cosmos").lower()
if _METADATA_BACKEND == "mongo":
    from utility.mongo_document_store import get_database as _get_mongo_db
    print(f"[metadata-db] (main) backend=mongo db={os.getenv('MONGO_DATABASE_NAME')}")
    database = _get_mongo_db(COSMOS_DATABASE_NAME)
else:
    print(f"[metadata-db] (main) backend=cosmos db={COSMOS_DATABASE_NAME}")
    client   = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
    database = client.get_database_client(COSMOS_DATABASE_NAME)
# Legacy Cosmos init (kept for rollback reference):
# client   = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
# database = client.get_database_client(COSMOS_DATABASE_NAME)

key                       = AZURE_SEARCH_ADMIN_KEY
azure_search_credential   = AzureKeyCredential(key)
feedback_container        = database.get_container_client("gi_qa")
search_client             = SearchClient(
    endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
    index_name=AZURE_SEARCH_INDEX,
    credential=azure_search_credential
)
search_client_share_point = SearchClient(
    endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,
    index_name=AZURE_SHARE_POINT_INDEXES_NAME,
    credential=azure_search_credential
)
storage_connection_string = _clean_env(os.getenv("BLOB_STORAGE_CONNECTION_STRING"))
container_name            = _clean_env(os.getenv("BLOB_STORAGE_CONTAINER_NAME"))

COSMOS_CONTAINER_NAMES = {
    "config":      _clean_env(os.getenv("CONFIG_CONTAINER_NAME"), "config"),
    "category":    _clean_env(os.getenv("CATEGORY_CONTAINER_NAME"), "gi_category"),
    "qa":          _clean_env(os.getenv("QA_CONTAINER_NAME"), "gi_qa"),
    "upload":      _clean_env(os.getenv("UPLOAD_CONTAINER_NAME"), "gi_uploads"),
    "user":        _clean_env(os.getenv("USER_CONTAINER_NAME"), "gi_users"),
    "transaction": _clean_env(os.getenv("TRANSACTION_CONTAINER_NAME"), "transactions"),
}


def _validate_cosmos_configuration() -> None:
    """Log/validate the active metadata DB (Cosmos or Mongo) at startup."""
    tag = f"[metadata-db:{_METADATA_BACKEND}]"
    print(
        tag, "database=", COSMOS_DATABASE_NAME,
        " containers=", COSMOS_CONTAINER_NAMES,
    )
    try:
        database.read()
        for name in COSMOS_CONTAINER_NAMES.values():
            database.get_container_client(name).read()
        print(tag, "validation succeeded.")
    except Exception as exc:
        print(tag, "validation failed:", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run at startup
    _validate_cosmos_configuration()
    asyncio.create_task(setupService.create_service())
    yield
    # Run on shutdown
    print('It is shutting down...')


app = FastAPI(lifespan=lifespan)
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def datatimeupdate():
    return datetime.datetime.now()


def try_parse_final_answer(value):
    """
    Extracts final_answer JSON from NAT / AutoGen output.
    Handles raw strings, markdown fences, and APPROVE suffix.
    """
    if isinstance(value, dict):
        if "final_answer" in value:
            return value
        return None

    text = str(value or "").strip()
    if not text:
        return None

    text = text.replace("```json", "").replace("```", "").strip()
    text = text.replace("APPROVE", "").strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "final_answer" in parsed:
            return parsed
    except Exception:
        pass

    start = text.find("{")
    end   = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict) and "final_answer" in parsed:
                return parsed
        except Exception:
            pass

    return None


def normalize_nat_answer(nat_payload):
    """
    Converts NAT response into the same answer format expected by the UI:
    {
      "final_answer": [
        {"type": "sql", "text": "..."},
        {"type": "llm", "text": "..."}
      ]
    }
    """
    # Case 1: NAT directly returns {"final_answer": [...]}
    if isinstance(nat_payload, dict) and "final_answer" in nat_payload:
        return nat_payload

    # Case 2: NAT returns {"answer": {"final_answer": [...]}}
    if isinstance(nat_payload, dict) and isinstance(nat_payload.get("answer"), dict):
        if "final_answer" in nat_payload["answer"]:
            return nat_payload["answer"]

    # Case 3: NAT returns output/result/response/content/value
    if isinstance(nat_payload, dict):
        for key in ["output", "result", "response", "content", "value"]:
            value = nat_payload.get(key)
            if value:
                if key == "value" and isinstance(value, str):
                    try:
                        nested = json.loads(value)
                        nested_answer = normalize_nat_answer(nested)
                        if nested_answer:
                            return nested_answer
                    except Exception:
                        pass
                parsed = try_parse_final_answer(value)
                if parsed:
                    return parsed

    # Case 4: NAT returns raw string
    if isinstance(nat_payload, str):
        parsed = try_parse_final_answer(nat_payload)
        if parsed:
            return parsed
        return {
            "final_answer": [
                {"type": "llm", "text": nat_payload}
            ]
        }

    # Final fallback
    return {
        "final_answer": [
            {"type": "llm", "text": str(nat_payload)}
        ]
    }


def sanitize_final_answer(answer_obj):
    """
    Clean final_answer text for UI readability:
    - strip markdown emphasis markers
    - remove wrapping quotes
    - suppress redundant SQL meta lines like "The SQL query confirms..."
    """
    if not isinstance(answer_obj, dict):
        return answer_obj
    items = answer_obj.get("final_answer")
    if not isinstance(items, list):
        return answer_obj

    cleaned = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "llm").strip()
        text      = str(item.get("text") or "").strip()
        if not text:
            continue

        text = text.replace("**", "")
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
            text = text[1:-1].strip()
        text = re.sub(r"\s+", " ", text).strip()

        if item_type.lower() == "sql" and re.search(
            r"\b(sql query|query confirms|sql result)\b", text, re.IGNORECASE
        ):
            continue

        cleaned.append({"type": item_type, "text": text})

    if cleaned:
        return {"final_answer": cleaned}
    return answer_obj


def extract_answer_text_and_plot(nat_payload):
    """
    Return a clean final answer string and optional plot_base64.
    Supports NAT payloads wrapped in {"value": "<json>"}.
    """
    payload = nat_payload
    if isinstance(payload, dict) and isinstance(payload.get("value"), str):
        try:
            payload = json.loads(payload["value"])
        except Exception:
            pass

    plot_base64 = None
    token_usage = 0

    if isinstance(payload, dict):
        token_usage = int(payload.get("token_usage") or 0)
        plot_base64 = payload.get("plot_base64")

    normalized = sanitize_final_answer(normalize_nat_answer(payload))
    parts = []
    if isinstance(normalized, dict):
        for item in normalized.get("final_answer", []):
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    parts.append(text)

    final_text = " ".join(parts).strip()
    if not final_text:
        final_text = str(payload if payload is not None else "").strip()

    return normalized, final_text, plot_base64, token_usage


async def call_nat_workflow(query):
    """
    Calls the NeMo Agent Toolkit workflow service and normalizes the output
    into the existing frontend response contract.
    """
    nat_start = time.time()
    try:
        async with httpx.AsyncClient(timeout=NAT_WORKFLOW_TIMEOUT_SEC) as client:
            response = await client.post(
                NAT_WORKFLOW_URL,
                json={"user_input": query}
            )
            response.raise_for_status()
    finally:
        print(f"[latency][service] nat_workflow_call_sec={time.time() - nat_start:.3f}")

    try:
        nat_payload = response.json()
    except Exception:
        nat_payload = response.text

    formatted_answer, final_answer_text, plot_base64, token_usage = extract_answer_text_and_plot(nat_payload)

    response_payload = {
        "data_points":   {},
        "answer":        formatted_answer,
        "answer_text":   final_answer_text,
        "thoughts":      "",
        "sql_query":     "",
        "token_usage":   token_usage,
        "credit_used":   0,
        "feedback":      "",
        "nat_metadata": {
            "service_layer":    "nemo-agent-toolkit",
            "workflow_url":     NAT_WORKFLOW_URL,
            "orchestration":    "autogen-agentchat",
            "model_provider":   "nvidia-nim",
            "latency_sec":      round(time.time() - nat_start, 3),
        }
    }
    if plot_base64:
        response_payload["plot_base64"] = plot_base64
    return response_payload


@app.post("/generate_response")
async def ask_api_call(request: Request):
    req_start         = time.time()
    request_json      = await request.json()
    service_latencies = {}

    email        = request_json.get("email")
    index_type   = request_json.get("index_type")
    explain_code = request_json.get("explain_code")
    print('email', email)

    balance_start = time.time()
    has_balance   = check_balance(email)
    service_latencies["check_balance_sec"] = round(time.time() - balance_start, 3)
    print(f"[latency][service] check_balance_sec={service_latencies['check_balance_sec']:.3f}")

    if has_balance:
        try:
            start_time               = time.time()
            start_time_query_result_1 = datatimeupdate()
            print('start_time_query_result_1', start_time_query_result_1)

            query = request_json["question"]

            # =====================================================
            # INPUT GUARDRAILS
            # =====================================================
            input_check = check_input(query)
            if not input_check["allowed"]:
                blocked_msg = input_check.get(
                    "message",
                    "This request has been blocked due to safety policy restrictions.",
                )
                total = round(time.time() - req_start, 3)
                print(f"[latency][total] generate_response_total_sec={total:.3f}")
                return JSONResponse(
                    content={
                        "data_points":       {},
                        "answer": {
                            "final_answer": [
                                {"text": blocked_msg, "type": "llm"},
                                {"text": "",          "type": "llm"},
                            ],
                        },
                        "answer_text":       blocked_msg,
                        "thoughts":          "",
                        "sql_query":         "",
                        "token_usage":       0,
                        "credit_used":       0,
                        "feedback":          "",
                        "dbresponse":        0,
                        "guardrail_blocked": True,
                        "guardrail_stage":   "input",
                        "service_latencies": service_latencies,
                        "total_latency_sec": total,
                    },
                    status_code=200,
                )

            useai            = request_json["useai"]
            include_category = request_json["overrides"]["include_category"]

            cat_start = time.time()
            cat_list  = await get_all_categories()
            service_latencies["get_all_categories_sec"] = round(time.time() - cat_start, 3)
            print(f"[latency][service] get_all_categories_sec={service_latencies['get_all_categories_sec']:.3f}")

            include_category.extend(cat['id'] for cat in cat_list)

            if useai == 0:
                query_params = []

                if include_category:
                    include_category = sorted(include_category)
                    query_string = """
                    SELECT *
                    FROM r
                    WHERE {conditions}
                        AND r.feedback = @feedback
                        AND r.question = @question
                    ORDER BY r.createdAt DESC
                    """
                    query_params = [
                        {"name": "@feedback", "value": 1},
                        {"name": "@question", "value": query},
                    ]
                    filter_conditions = " AND ".join([
                        f'ARRAY_CONTAINS(r.include_category, "{i}")'
                        for i in include_category
                    ])
                    sql = query_string.format(conditions=filter_conditions)
                else:
                    sql = (
                        "SELECT * FROM gi_qa r "
                        "WHERE r.include_category = [] "
                        "and r.feedback = 1 "
                        "and r.question = '" + query + "' "
                        "order by r.createdAt desc"
                    )

                askResponse = {}

                qa_lookup_start = time.time()
                query_result    = feedback_container.query_items(
                    query=sql,
                    parameters=query_params,
                    enable_cross_partition_query=True,
                    max_item_count=1
                )
                service_latencies["qa_exact_lookup_sec"] = round(time.time() - qa_lookup_start, 3)
                print(f"[latency][service] qa_exact_lookup_sec={service_latencies['qa_exact_lookup_sec']:.3f}")

                qa_record = None
                for item in query_result:
                    qa_record = item
                    break

                if not qa_record:
                    match_found   = None
                    similar_start = time.time()
                    match_found   = await get_similar_qa(query)
                    service_latencies["qa_similarity_lookup_sec"] = round(time.time() - similar_start, 3)
                    print(f"[latency][service] qa_similarity_lookup_sec={service_latencies['qa_similarity_lookup_sec']:.3f}")
                    print("matchfound", match_found)

                    if match_found is None:
                        filter = None
                        if include_category:
                            include_filter = " or ".join(
                                f"category eq '{category}'"
                                for category in include_category
                            )
                            filter = f"({include_filter})"

                        print("-----------------Agenting Call happened-------------")
                        print("-----------------NAT Workflow Call happened-------------")
                        askResponse = await call_nat_workflow(query)
                        service_latencies["nat_workflow_sec"] = askResponse.get("nat_metadata", {}).get("latency_sec", 0)
                        print(f"[latency][service] nat_workflow_sec={service_latencies['nat_workflow_sec']:.3f}")

                        askResponse["dbresponse"]      = 0
                        askResponse["guardrail_blocked"] = False

                        token_usage  = askResponse.get("token_usage", 0)
                        update_start = time.time()
                        askResponse  = await process_query_and_update(
                            email,
                            query,
                            token_usage,
                            askResponse,
                            start_time,
                            include_category=None
                        )
                        service_latencies["process_query_update_sec"] = round(time.time() - update_start, 3)
                        print(f"[latency][service] process_query_update_sec={service_latencies['process_query_update_sec']:.3f}")

                    else:
                        askResponse['answer']          = match_found[0]['answer']
                        askResponse['thoughts']        = match_found[0]['thoughts']
                        askResponse['data_points']     = ast.literal_eval(match_found[0]['data_points'])
                        askResponse['dbresponse']      = 1
                        askResponse['token_usage']     = 0
                        askResponse['credit_used']     = 0
                        askResponse['feedback']        = ""
                        askResponse["guardrail_blocked"] = False

                else:
                    askResponse['answer']          = qa_record['answer']
                    askResponse['dbresponse']      = 1
                    askResponse['thoughts']        = qa_record['thoughts']
                    askResponse['data_points']     = qa_record['data_points']
                    askResponse['token_usage']     = 0
                    askResponse['credit_used']     = 0
                    askResponse['feedback']        = ""
                    askResponse["guardrail_blocked"] = False

            else:
                filter = None
                if include_category:
                    include_filter = " or ".join(
                        f"category eq '{category}'"
                        for category in include_category
                    )
                    filter = f"({include_filter})"

                print("-----------------Agenting Call happened-------------")
                print("-----------------NAT Workflow Call happened-------------")
                askResponse = await call_nat_workflow(query)
                service_latencies["nat_workflow_sec"] = askResponse.get("nat_metadata", {}).get("latency_sec", 0)
                print(f"[latency][service] nat_workflow_sec={service_latencies['nat_workflow_sec']:.3f}")

                # =====================================================
                # OUTPUT GUARDRAILS
                # =====================================================
                output_check = check_output(askResponse.get("answer", ""))
                if not output_check["allowed"]:
                    blocked_msg = output_check.get("text") or (
                        "This response has been blocked due to safety policy restrictions."
                    )
                    # Match the success-path shape the UI expects:
                    #   answer = { "final_answer": [ {text, type}, ... ] }
                    # Anything else makes the Insights tab silently render empty.
                    askResponse["answer"] = {
                        "final_answer": [
                            {"text": blocked_msg, "type": "llm"},
                            {"text": "",          "type": "llm"},
                        ],
                    }
                    askResponse["answer_text"]      = blocked_msg
                    askResponse["sql_query"]        = ""
                    askResponse["python_code"]      = ""
                    askResponse["plot_base64"]      = ""
                    askResponse["guardrail_blocked"] = True
                    askResponse["guardrail_stage"]   = "output"
                else:
                    askResponse["guardrail_blocked"] = False

                askResponse['dbresponse'] = 0

                token_usage  = askResponse.get("token_usage", 0)
                update_start = time.time()
                askResponse  = await process_query_and_update(
                    email,
                    query,
                    token_usage,
                    askResponse,
                    start_time,
                    include_category=None
                )
                service_latencies["process_query_update_sec"] = round(time.time() - update_start, 3)
                print(f"[latency][service] process_query_update_sec={service_latencies['process_query_update_sec']:.3f}")

            askResponse["service_latencies"] = service_latencies
            askResponse["total_latency_sec"] = round(time.time() - req_start, 3)
            print(f"[latency][total] generate_response_total_sec={askResponse['total_latency_sec']:.3f}")
            return JSONResponse(content=askResponse, status_code=200)

        except httpx.ReadTimeout:
            total = round(time.time() - req_start, 3)
            print(f"[latency][total] generate_response_total_sec={total:.3f}")
            timeout_msg = "The request is taking longer than expected. Please try again."
            return JSONResponse(
                {
                    "answer": {
                        "final_answer": [
                            {"text": timeout_msg, "type": "llm"},
                            {"text": "",          "type": "llm"},
                        ],
                    },
                    "answer_text": timeout_msg,
                    "data_points": {},
                    "thoughts": "",
                    "sql_query": "",
                    "token_usage": 0,
                    "credit_used": 0,
                    "feedback": "",
                    "dbresponse": 0,
                    "error": "NAT workflow timed out",
                    "guardrail_blocked": False,
                    "total_latency_sec": total,
                    "service_latencies": service_latencies,
                },
                status_code=200,
            )
        except Exception as e:
            print(str(e))
            logging.exception("Exception in /ask")
            total = round(time.time() - req_start, 3)
            print(f"[latency][total] generate_response_total_sec={total:.3f}")
            return JSONResponse({"error": str(e)}, status_code=500)

    else:
        print("Insufficient balance for user:", email)
        return JSONResponse(
            {"Message": "Insufficient balance. Please add credits to proceed further"},
            status_code=403
        )


@app.get("/citationPdf")
async def get_pdf_page(
    blob_name:   str = Query(..., description="Name of the PDF blob in the storage"),
    page_number: int = Query(..., description="Page number to extract")
):
    if page_number is not None:
        page_number = int(page_number) - 1  # PyMuPDF uses zero-based indexing

    all_blob_names = list_blob_files()
    blob_filename  = max(all_blob_names, key=lambda x: similar(blob_name, x))

    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    blob_client         = blob_service_client.get_blob_client(container=container_name, blob=blob_filename)

    download_stream = blob_client.download_blob()
    pdf_content     = download_stream.readall()

    pdf_document = fitz.open(stream=pdf_content, filetype="pdf")

    if page_number is not None and page_number < len(pdf_document):
        pdf_writer = fitz.open()
        pdf_writer.insert_pdf(pdf_document, from_page=page_number, to_page=page_number)
        pdf_bytes  = pdf_writer.write()
    else:
        return JSONResponse(
            content={"success": False, "message": "Page number out of range"},
            status_code=400
        )

    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf")


# Health API
@app.get("/health")
async def health_check():
    try:
        return {"status": "API is accessible", "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail="API not accessible")


# This API updates the feedback of a previously asked question by ID.
@app.put("/questionFeedback")
async def update_feedback(request: Request):
    try:
        request_json = await request.json()
        id       = request_json.get('id')
        feedback = request_json.get('feedback')

        user_name    = "super-admin"
        query        = "SELECT * FROM gi_qa r WHERE r.id = @id"
        query_params = [{"name": "@id", "value": str(id)}]

        query_result = feedback_container.query_items(
            query=query,
            parameters=query_params,
            enable_cross_partition_query=True
        )

        qa_record = None
        for item in query_result:
            qa_record = item

        if not qa_record:
            return {"message": "Question with ID {} not found".format(id)}

        qa_record['feedback']  = feedback
        qa_record['updatedBy'] = user_name
        qa_record['updatedAt'] = str(datetime.datetime.now())

        response = feedback_container.replace_item(item=qa_record, body=qa_record)

        if feedback == 1:
            str_id = str(qa_record['id'])
            qna_indexing(
                str_id,
                qa_record['question'],
                qa_record['answer'],
                qa_record['thoughts'],
                str(qa_record['data_points']),
                str(qa_record['include_category'])
            )

        return {"message": "Feedback updated successfully for question with ID {}".format(id)}

    except Exception as e:
        return {"message": "Error occurred while updating feedback: " + str(e)}


def create_app():
    app.include_router(
        userManagementRouter.router,
        prefix="/userCreditService",
        tags=["User Credit Service"]
    )
    app.include_router(
        categoryManagementRouter.router,
        prefix="/documentService",
        tags=["Document Service"]
    )
    app.include_router(
        dbConnectionRouter.router,
        prefix="/dbConnectionRouter",
        tags=["DB Connection Service"]
    )
    app.include_router(
        configManagementRouter.router,
        prefix="/configManagementRouter",
        tags=["Config Service"]
    )
    app.include_router(
        uploadManagementRouter.router,
        prefix="/uploadManagementRouter",
        tags=["Upload Service"]
    )
    return app


app = create_app()
