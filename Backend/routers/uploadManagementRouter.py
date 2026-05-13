from sqlalchemy import create_engine
from sqlalchemy.engine import reflection
 
from pydantic import BaseModel
from datetime import datetime
from fastapi import Request, HTTPException,Form, status, APIRouter,Query, UploadFile, File
import urllib
import os
from azure.cosmos import CosmosClient
from fastapi.responses import JSONResponse, FileResponse
from azure.cosmos import exceptions
from typing import Optional, List
import asyncio
import uuid
from azure.storage.blob import BlobServiceClient
import json
from azure.storage.queue import QueueClient
import time
import traceback
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from utility.documentServiceHelper import *
from utility.helper import *
 
 
 
 
router = APIRouter()
 
 
# SQLdb credentials Parameters (provided via API payload; do not hardcode)
driver = 'ODBC Driver 18 for SQL Server'
# encoding = 'ISO-8859-1'
 
# Step 1: Connection string for Azure SQL Database
# connection_string = f'mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}")}'
 
# Create the SQLAlchemy engine
 
COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
 
client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
database = client.get_database_client(COSMOS_DATABASE_NAME)
BLOB_STORAGE_CONTAINER_NAME=os.getenv("BLOB_STORAGE_CONTAINER_NAME")
BLOB_STORAGE_CONNECTION_STRING = os.getenv("BLOB_STORAGE_CONNECTION_STRING")
 
blob_service_client= BlobServiceClient.from_connection_string(BLOB_STORAGE_CONNECTION_STRING)
 
container_client = blob_service_client.get_container_client(BLOB_STORAGE_CONTAINER_NAME)
 
upload_container = database.get_container_client("gi_uploads")
transaction_container = database.get_container_client("transactions")
user_container = database.get_container_client("gi_users")
 
service_endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]
azure_search_admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
 
azure_search_credential = AzureKeyCredential(azure_search_admin_key)
search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=azure_search_credential)
 
QUEUE_NAME = os.getenv("AZURE_GRAPHRAG_QUEUE_STORAGE_NAME")
QUEUE_CLIENT = QueueClient.from_connection_string(BLOB_STORAGE_CONNECTION_STRING, QUEUE_NAME)
 
 
 


@router.post("/uploadFile")
async def create_upload_file(
    files: List[UploadFile] = File(...),
    email: str = Form(...),
    category_id: str = Form(...),
    remarks: Optional[str] = Form(None),
    vector_rag: str = Form(...),
    graph_rag: str = Form(...),
):
    try:
        query = "SELECT c.file_name FROM gi_uploads c"
        file_list = list(upload_container.query_items(query, enable_cross_partition_query=True))
        print("fileslisttt:", file_list)

        dup_list = [file_item['file_name'] for file_item in file_list]

        uploaded_files = []
        not_uploaded_files = []
        graph_rag_files = []
        
        blob_list = list(container_client.list_blobs())
        print("All blobs in the container:")
        for blob in blob_list:
            print(blob.name)

        
        # ✅ Step 1: List all blobs inside the specific folder
        def list_blobs_in_path(path_prefix):
            blob_list = list(container_client.list_blobs(name_starts_with=path_prefix))
            if not blob_list:
                print(f"No blobs found in path: {path_prefix}")
            return blob_list

        # ✅ Step 2: Delete all files inside the folder (but not the folder itself)
        def delete_files_in_folder(path_prefix):
            blobs_to_delete = list_blobs_in_path(path_prefix)
            
            if not blobs_to_delete:
                return
            
            for blob in blobs_to_delete:
                print(f"Deleting file: {blob.name}")
                container_client.get_blob_client(blob.name).delete_blob(delete_snapshots="include")
            
            print(f"All files inside '{path_prefix}' deleted successfully.")

        for file in files:
            file_name = file.filename.replace(" ", "_").replace("'", "").replace("(", "").replace(")", "").replace("&", "")
            file_id = uuid.uuid4()

            try:
                if file_name not in dup_list:
                    uploaded_files.append(file_name)
                    file_path = os.path.join(os.getcwd(), 'uploads', file_name)
                    print(file_path)
                    with open(file_path, "wb") as file_content:
                        file_content.write(file.file.read())

                    file_info = os.stat(file_path)
                    file_size = file_info.st_size

                    item = {
                        'id': str(file_id),
                        'file_name': file_name,
                        'file_size': file_size,
                        'uploaded_by': email,
                        'uploaded_at': str(datetime.now()),
                        'chunk_ids': '',
                        'token_used': '',
                        'credit_used': '',
                        'category_id': category_id,
                        'ex_time': time.time(),
                        'status': 0,
                        'graphrag_index_status': 0,
                        'remarks': remarks
                    }

                    # Check upload mode
                    if vector_rag.lower() == "true":
                        item['vector_rag'] = vector_rag
                        chunk_ids = handle_vector_upload(file_path, file_name, file_id, email)
                        if chunk_ids:
                            item['chunk_ids'] = chunk_ids
                        print(f"Uploading in vector_rag mode: {file_name}")

                    if graph_rag.lower() == "true":
                        item['graph_rag'] = graph_rag
                        graph_rag_files.append({
                            "file_path": file_path,
                            "file_name": file_name,
                            "category_id": category_id
                        })

                    upload_container.create_item(body=item)

                else:
                    not_uploaded_files.append(file_name)

            except Exception as file_processing_error:
                traceback.print_exc()
                return {"message": f"Error processing file {file_name}: {str(file_processing_error)}", "status": "error"}

        # Process graph_rag indexing after all files are uploaded
                

        # ✅ Upload new files
        if graph_rag_files:
            root_path = os.path.join(os.getcwd(), 'data')
            print('graph_rag_files', graph_rag_files)

            for file_data in graph_rag_files:
                file_path = file_data["file_path"]
                file_name = file_data["file_name"]
                category_id = file_data["category_id"]

                blob_name = os.path.basename(file_path)
                blob_client = container_client.get_blob_client(blob_name)
                print(f"Uploading new file: {blob_name}")
                
                # Call delete function before uploading new files
                # delete_files_in_folder("graphraginput/input/")

                with open(file_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)

                process_pdf_blob(file_name)
                    
            
            msg = json.dumps({"graph_rag_files": graph_rag_files, "data_dir": root_path, "category_id": category_id})
            QUEUE_CLIENT.send_message(msg)
            # os.remove(file_path)
            print(f"Graph RAG indexing completed for: {file_name}")

        if uploaded_files:
            return {"message": "Files uploaded successfully.", "filename": ", ".join(uploaded_files), "status": "success"}
        elif not_uploaded_files:
            return {"message": "Files already exist and were not uploaded.", "filename": ", ".join(not_uploaded_files), "status": "success"}
        else:
            return {"message": "No files uploaded. All files already exist.", "filename": "", "status": "success"}

    except Exception as e:
        traceback.print_exc()
        return {"message": "Error occurred while uploading files: " + str(e), "status": "error"}


 
 
 
 
@router.get("/uploadedFilesList/")
async def uploaded_files_list(email: str = Query(...), category_id: str = None, filename: str = None):
    try:
        # Your existing logic to calculate balance
        print("email:", email)
        balance = calculate_balance(email)
 
        # Fetch user details including role
        user_query = f"SELECT * FROM c WHERE c.email = '{email}'"
        user_query_result = user_container.query_items(query=user_query, enable_cross_partition_query=True)
        user_details = list(user_query_result)
 
        if not user_details:
            raise HTTPException(status_code=404, detail="User not found.")
 
        # Extract the role from user details
        user_role = user_details[0]['role']
        user_categories = user_details[0]['categories'] or []
        category_list = ','.join([f"'{cat}'" for cat in user_categories])
 
        # Check if the user role is 'Admin'
        if user_role == 'Admin':
            # Fetch all uploads
            upload_query = f"SELECT * FROM c WHERE c.category_id IN ({category_list})"
            if category_id is not None:
                upload_query += f" AND c.category_id = '{category_id}'"
            if filename is not None:
                upload_query += f" WHERE c.file_name = '{filename}'"
   
            query_result = upload_container.query_items(query=upload_query, enable_cross_partition_query=True)
        else:
            # Fetch uploads based on the user's email
            upload_query = f"SELECT * FROM c WHERE c.uploaded_by = '{email}' AND c.category_id IN ({category_list})"
            if category_id is not None:
                upload_query += f" AND c.category_id = '{category_id}'"
            if filename is not None:
                upload_query += f" WHERE c.file_name = '{filename}'"
            query_result = upload_container.query_items(query=upload_query, enable_cross_partition_query=True)
        uploaded_files = list(query_result)
        response_data = {"Files": uploaded_files, "balance": balance}
        return JSONResponse(response_data)
 
    except exceptions.CosmosHttpResponseError as e:
        return JSONResponse(content={"message": f"Cosmos DB error: {str(e)}"}, status_code=500)
    except Exception as e:
        return JSONResponse(content={"message": f"Error occurred: {str(e)}"}, status_code=500)
   
 
@router.post('/deleteFile')
async def delete_chunks_by_title(request: Request):
    try:
        raw_data = await request.json()
        print("*****************raw_data********************", raw_data)
 
        # ------STEP 1: DELETE INDEXES FROM VECTOR STORE------
        ids = [id for id in raw_data.get("chunk_ids", []) if str(id).strip()]
        if ids:
            backend = (os.getenv("VECTOR_SEARCH_BACKEND") or "azure").strip().lower()
            if backend in ("zilliz", "milvus"):
                from utility.zilliz_client import delete_chunks_by_ids as zilliz_delete
                zilliz_delete(ids)
                print(f"Step 1 finished (Zilliz): deleted {len(ids)} chunks")
            else:
                docid = [{'id': i} for i in ids]
                search_client.delete_documents(documents=docid)
                print("Step 1 finished (Azure Search)")
 
        # ------STEP 2: DELETE FILE FROM BLOB STORAGE------
        blob_name = raw_data.get("blob_name")
        if blob_name:
            blob_client = blob_service_client.get_blob_client(container=BLOB_STORAGE_CONTAINER_NAME, blob=blob_name)
            try:
                blob_client.delete_blob()
                print(f"Deleted blob: {blob_name}")
            except Exception as e:
                print(f"Blob '{blob_name}' not found")
 
 
        query = "SELECT * FROM gi_uploads r WHERE r.file_name = @blob_name"
        query_params = [{"name": "@blob_name", "value": str(blob_name)}]
 
        # Execute the parameterized query
        items = list(upload_container.query_items(query=query, parameters=query_params, enable_cross_partition_query=True))
 
        print(f"Query result: {items}")
 
        # Check if any items were found before attempting deletion
        if items:
            for item in items:
                print("items in blob :", item)
                partition_key_value = item['id']
                print(f"Attempting to delete item with partition key: {partition_key_value}")
                upload_container.delete_item(item['id'], partition_key=partition_key_value)
 
 
            return JSONResponse(content=f"File entry with file_name '{blob_name}' deleted successfully")
        else:
            print(f"File entry with file_name '{blob_name}' not found")
            # Send record deleted alert
 
            return JSONResponse(content=f"File entry with file_name '{blob_name}' not found ")
 
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"An error occurred while deleting file entries: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
   
   
 
 
 
@router.post('/downloadFile')
async def download_file(request: Request):
    """
    Downloads a file from Azure Blob Storage based on the provided blob_name.
    """
    raw_data = await request.json()
    blob_name = raw_data.get("blob_name")
    try:
        # Get the blob client for the specified file
        blob_client = blob_service_client.get_blob_client(container=BLOB_STORAGE_CONTAINER_NAME, blob=blob_name)
       
        # Check if the blob exists
        try:
            blob_properties = blob_client.get_blob_properties()
            print(f"Blob found: {blob_name}")
        except Exception as e:
            print(f"Blob '{blob_name}' not found: {e}")
            return JSONResponse(content=f"Blob '{blob_name}' not found", status_code=404)
 
        # Download the blob content to a local temporary file
        download_file_path = os.path.join(os.getcwd(), "downloads", blob_name)
        os.makedirs(os.path.dirname(download_file_path), exist_ok=True)
 
        with open(download_file_path, "wb") as download_file:
            blob_data = blob_client.download_blob()
            download_file.write(blob_data.readall())
            print(f"Blob '{blob_name}' downloaded successfully to {download_file_path}")
 
        # Return the file as a response
        return FileResponse(
            path=download_file_path,
            media_type="application/octet-stream",
            filename=blob_name
        )
 
    except Exception as e:
        print(f"An error occurred while downloading the file: {str(e)}")
        return JSONResponse(content=f"An error occurred while downloading the file: {str(e)}", status_code=500)
 