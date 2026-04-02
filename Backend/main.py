import uvicorn
import os
import logging
import os
import aiohttp
import openai
import ast
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services import userCreditService,documentService,setupService
from routers import categoryManagementRouter, userManagementRouter, dbConnectionRouter, configManagementRouter, uploadManagementRouter
#from azure.monitor.opentelemetry import configure_azure_monitor
#from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from dotenv import load_dotenv
from azure.cosmos import CosmosClient
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from utility.helper import *
from utility.acsServiceHelper import get_similar_qa
from azure.search.documents.aio import SearchClient
from azure.core.credentials import AzureKeyCredential
from PyPDF2 import PdfReader, PdfWriter
import fitz
import re
import datetime
from urllib.parse import unquote_plus
from azure.storage.blob import BlobServiceClient
import io
import asyncio
from contextlib import asynccontextmanager
from utility.inference import *
from utility.acsServiceHelper import qna_indexing
 

load_dotenv("unified.env")

# Set logging level to ERROR or CRITICAL
logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.ERROR)
logging.getLogger('azure.monitor.opentelemetry.exporter.export._base').setLevel(logging.ERROR)

AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX_NAME")
AZURE_QNA_INDEX = os.getenv("AZURE_QA_INDEX_NAME")
AZURE_SHARE_POINT_INDEXR_NAME = os.getenv("AZURE_SHARE_POINT_INDEXR_NAME")
AZURE_SHARE_POINT_INDEXES_NAME = os.getenv("AZURE_SHARE_POINT_INDEXES_NAME")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_OPENAI_SERVICE_BASE = os.getenv("AZURE_OPENAI_API_BASE")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_TYPE = os.getenv("OPENAI_API_TYPE")
AZURE_OPENAI_CHATGPT_DEPLOYMENT = os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME")
AZURE_OPENAI_CHATGPT_MODEL = os.getenv("GPT3_LLM_MODEL_NAME")
AZURE_OPENAI_EMB_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
KB_FIELDS_CONTENT = 'content'
KB_FIELDS_SOURCEPAGE = 'sourcepage'


COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
TOKEN_PER_CREDIT = os.getenv("TOKEN_PER_CREDIT")

client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
database = client.get_database_client(COSMOS_DATABASE_NAME)

key = AZURE_SEARCH_ADMIN_KEY
azure_search_credential = AzureKeyCredential(key)
feedback_container = database.get_container_client("gi_qa")
search_client = SearchClient(endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,index_name=AZURE_SEARCH_INDEX, credential=azure_search_credential)
search_client_share_point = SearchClient(endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,index_name=AZURE_SHARE_POINT_INDEXES_NAME,indexes_name =AZURE_SHARE_POINT_INDEXES_NAME,credential=azure_search_credential )
storage_connection_string = os.getenv("BLOB_STORAGE_CONNECTION_STRING")
container_name = os.getenv("BLOB_STORAGE_CONTAINER_NAME")



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run at startup
    asyncio.create_task(setupService.create_service())
    yield
    # Run on shutdown (if required)
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


@app.post("/generate_response")
async def ask_api_call(request: Request):
    # start_time_complete_api_call =  datetime.datetime.now()
    request_json = await request.json()
    email = request_json.get("email")
    index_type = request_json.get("index_type")
    explain_code = request_json.get("explain_code")
    print('email',email)
    # token_usage = None
    # start_time_check_balance = datetime.datetime.now()
    if check_balance(email):
        try:
            start_time = time.time()
            start_time_query_result_1 =  datatimeupdate()
            print('start_time_query_result_1', start_time_query_result_1)
            query = request_json["question"]
            useai = request_json["useai"]
            include_category = request_json["overrides"]["include_category"]
            # start_time_get_inactive_categories =  datetime.datetime.now()
            cat_list = await get_all_categories()
            # end_time_get_inactive_categories = datetime.datetime.now()
            # time_taken_get_inactive_categories = (end_time_get_inactive_categories - start_time_get_inactive_categories).total_seconds()
            include_category.extend(cat['id'] for cat in cat_list)
            # request_json["overrides"]["include_category"] = include_category
            # start_time_total_open_call =  datetime.datetime.now()
      
            if useai == 0:
                
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
                    filter_conditions = " AND ".join([f'ARRAY_CONTAINS(r.include_category, "{i}")' for i in include_category])
                    sql = query_string.format(conditions=filter_conditions)
                else:
                    sql = "SELECT * FROM gi_qa r WHERE r.include_category = [] and r.feedback = 1 and r.question = '"+query+"' order by r.createdAt desc"



                askResponse = {}

                
                query_result = feedback_container.query_items(
                    query=sql,
                    parameters=query_params,
                    enable_cross_partition_query=True,
                    max_item_count=1
                )
       
 
                qa_record = None
                items = query_result
                for item in items:
                    # print('item', item)
                    qa_record = item
                    break
                # print("qa_record",qa_record)
                if not qa_record:
                    # Similar
                    match_found = None
                    match_found = await get_similar_qa(query)
                    print("matchfound",match_found)
                    # Determine which search_client to use based on index_type

                    if match_found == None:
                        filter = None
                        # Handle include_category
                        if include_category:
                            include_filter = " or ".join(f"category eq '{category}'" for category in include_category)
                            filter = f"({include_filter})"
                        # print('!!!!!!!!!!!!!!! include_category[0] !!!!!!!!!!!!!!!!!!!!!', include_category[0])
                        print("-----------------Agenting Call happened-------------")
                        
                        askResponse = await start_agenting_process(query, index_type, filter, explain_code,include_category[0], email)
                        askResponse["dbresponse"] = 0
                        token_usage = askResponse.get("token_usage")

                        askResponse = await process_query_and_update(email,query, token_usage, askResponse, start_time, 
                        include_category=None)
 
                    else:
                        askResponse['answer'] = match_found[0]['answer']
                        askResponse['thoughts'] = match_found[0]['thoughts']
                        askResponse['data_points'] = ast.literal_eval(match_found[0]['data_points'])
                        askResponse['dbresponse'] = 1
                        askResponse['token_usage'] = 0
                        askResponse['credit_used'] = 0
                        token_usage = 0
                        credit_used = 0
                        askResponse['feedback'] = ""
                else:
                    askResponse['answer']  = qa_record['answer']
                    askResponse['dbresponse'] = 1
                    askResponse['thoughts'] = qa_record['thoughts']
                    askResponse['data_points'] = qa_record['data_points']
                    askResponse['token_usage'] = 0
                    askResponse['credit_used'] = 0
                    askResponse['feedback'] = ""
                    token_usage = 0
 
            else:
               
                filter = None
                # Handle include_category
                if include_category:
                    include_filter = " or ".join(f"category eq '{category}'" for category in include_category)
                    filter = f"({include_filter})"
                print("-----------------Agenting Call happened-------------")
                askResponse = await start_agenting_process(query, index_type, filter, explain_code,include_category[0], email)
 
                # print('response', askResponse)
                askResponse['dbresponse'] = 0
           
                token_usage = askResponse.get("token_usage")
                askResponse = await process_query_and_update(email,query, token_usage, askResponse, start_time,
                include_category=None)

            return JSONResponse(content=askResponse, status_code=200)
       
        except Exception as e:
            print(str(e))
            logging.exception("Exception in /ask")
            return JSONResponse({"error": str(e)}, status_code=500)
 
    else:
        print("Insufficient balance for user:", email)
        return JSONResponse({"Message": "Insufficient balance. Please add credits to proceed further"}, status_code=403)
 

 




@app.get("/citationPdf")
async def get_pdf_page(blob_name: str = Query(..., description="Name of the PDF blob in the storage"),page_number: int = 	Query(..., description="Page number to extract")):
    # Extract page number from the blob name
    # page_number = extract_page_number(blob_name)
    # print('page_number', page_number)
    if page_number is not None:
        page_number = int(page_number) - 1  # PyMuPDF uses zero-based indexing

    # Get all blob names and find the most similar one
    all_blob_names = list_blob_files()
    blob_filename = max(all_blob_names, key=lambda x: similar(blob_name, x))

    # Connect to the storage account
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection_string)
    # Get the blob client
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_filename)
    # Download the PDF file as a stream
    download_stream = blob_client.download_blob()
    pdf_content = download_stream.readall()

    # Load the PDF with PyMuPDF
    pdf_document = fitz.open(stream=pdf_content, filetype="pdf")

    if page_number is not None and page_number < len(pdf_document):
        # Extract the specific page and create a new PDF
        pdf_writer = fitz.open()
        pdf_writer.insert_pdf(pdf_document, from_page=page_number, to_page=page_number)
        pdf_bytes = pdf_writer.write()
    else:
        # Return the entire PDF if no valid page number is provided
        # pdf_bytes = pdf_content
        return JSONResponse(content={"success": False, "message": "Page number out of range"}, status_code=400)

    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf")




# Health API
@app.get("/health")
async def health_check():
    try:
        return {"status": "API is accessible", "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail="API not accessible")
    
#This API updates the feedback of a previously asked question by ID.
@app.put("/questionFeedback")
async def update_feedback(request: Request):
    try:
        request_json = await request.json()
        id = request_json.get('id')
        feedback = request_json.get('feedback')
 
        user_name ="super-admin"
        query = "SELECT * FROM gi_qa r WHERE r.id = @id"
        query_params = [{"name": "@id", "value": str(id)}]
 
        # Execute the parameterized query
        query_result = feedback_container.query_items(
            query=query,
            parameters=query_params,
            enable_cross_partition_query=True
        )
 
        # Print the query results
        qa_record = None
        for item in query_result:
            qa_record = item
        if not qa_record:
            return {"message": "Question with ID {} not found".format(id)}
 
        qa_record['feedback'] = feedback
        qa_record['updatedBy'] = user_name
        qa_record['updatedAt'] = str(datetime.datetime.now())
        response = feedback_container.replace_item(item=qa_record, body=qa_record)
 
        if feedback==1:
            str_id = str(qa_record['id'])
            qna_indexing(str_id,qa_record['question'],qa_record['answer'],qa_record['thoughts'],str(qa_record['data_points']), str(qa_record['include_category']))
 
        return {"message": "Feedback updated successfully for question with ID {}".format(id)}
    except Exception as e:
 
        return {"message": "Error occurred while updating feedback: " + str(e)}

def create_app():
	app.include_router(userManagementRouter.router, prefix="/userCreditService", tags=["User Credit Service"])
	# app.include_router(documentService.router, prefix="/documentService", tags=["Document Service"])
	app.include_router(categoryManagementRouter.router, prefix="/documentService", tags=["Document Service"])
	app.include_router(dbConnectionRouter.router, prefix="/dbConnectionRouter", tags=["DB Connection Service"])
	app.include_router(configManagementRouter.router, prefix="/configManagementRouter", tags=["Config Service"])
	app.include_router(uploadManagementRouter.router, prefix="/uploadManagementRouter", tags=["Upload Service"])
      
      


	return app

app = create_app()