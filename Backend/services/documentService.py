from fastapi import Request, HTTPException, File, UploadFile, Form,APIRouter,Query
from fastapi.responses import JSONResponse
from azure.storage.blob import BlobServiceClient
import os
from datetime import datetime
from azure.search.documents import SearchClient
from azure.cosmos import CosmosClient
from azure.core.credentials import AzureKeyCredential
import uuid
import traceback
from utility.acsServiceHelper import *
from utility.documentServiceHelper import *
from typing import List, Optional
import time
from typing import Optional
import json
from azure.search.documents.indexes.models import (
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndex,
    SearchIndexer,
    SimpleField,
    SearchFieldDataType,
)
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient

from azure.storage.queue import QueueClient

router = APIRouter()



service_endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]
azure_search_admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
azure_search_credential = AzureKeyCredential(azure_search_admin_key)
search_client = SearchClient(endpoint=service_endpoint, index_name=index_name, credential=azure_search_credential)


COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
# COSMOS_UPLOAD_CONTAINER = os.environ["COSMOS_UPLOAD_CONTAINER"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]


client = CosmosClient(url=COSMOS_ENDPOINT, credential=COSMOS_KEY)
database = client.get_database_client(COSMOS_DATABASE_NAME)
# container = database.get_container_client(COSMOS_UPLOAD_CONTAINER)
transaction_container = database.get_container_client("transactions")
user_container = database.get_container_client("gi_users")
upload_container = database.get_container_client("gi_uploads")

category_container = database.get_container_client("gi_category")
feedback_container = database.get_container_client("gi_qa")

BLOB_STORAGE_CONNECTION_STRING = os.getenv("BLOB_STORAGE_CONNECTION_STRING")
BLOB_STORAGE_CONTAINER_NAME=os.getenv("BLOB_STORAGE_CONTAINER_NAME")
blob_service_client= BlobServiceClient.from_connection_string(BLOB_STORAGE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(BLOB_STORAGE_CONTAINER_NAME)

# Share point key and endpoint details
azure_search_service_endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
azure_search_admin_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]
credential = AzureKeyCredential(azure_search_admin_key)
index_name = os.environ["AZURE_SHARE_POINT_INDEXES_NAME"]
indexer_name = os.environ["AZURE_SHARE_POINT_INDEXR_NAME"]
indexers_client = SearchIndexerClient(azure_search_service_endpoint, AzureKeyCredential(azure_search_admin_key))

QUEUE_NAME = os.getenv("AZURE_QUEUE_STORAGE_NAME")
QUEUE_CLIENT = QueueClient.from_connection_string(BLOB_STORAGE_CONNECTION_STRING, QUEUE_NAME)

@router.post("/uploadFile")
async def create_upload_file(
    files: List[UploadFile] = File(...),
    email: str = Form(...),
    category_id: str = Form(...),
    remarks: Optional[str] = None
):
    try:
        query = "SELECT c.file_name FROM gi_uploads c"
        file_list = list(upload_container.query_items(query, enable_cross_partition_query=True))
        print("fileslisttt:", file_list)

        dup_list = [file_item['file_name'] for file_item in file_list]

        uploaded_files = []
        not_uploaded_files = []

        for file in files:
            file_name = file.filename.replace(" ", "_").replace("'", "").replace("(","").replace(")","").replace("&","")
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
                        'remarks': remarks
                    }
                    upload_container.create_item(body=item)

                    print("file_path:", file_path)
                    blob_name = os.path.basename(file_path)
                    blob_client = container_client.get_blob_client(blob_name)
                    print("blob_name:", blob_name)
                    with open(file_path, "rb") as data:
                        blob_client.upload_blob(data, overwrite=True)
                        msg = json.dumps({"file_name": file_name,"file_id":str(file_id),"email":email})
                        QUEUE_CLIENT.send_message(msg)
                    os.remove(file_path)

                else:
                    not_uploaded_files.append(file_name)

            except Exception as file_processing_error:
                traceback.print_exc()
                return {"message": f"Error processing file {file_name}: {str(file_processing_error)}", "status": "error"}

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
        balance = calculate_balance(email,transaction_container)

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

        # ------STEP 1: DELETE INDEXES FROM ACS (Azure Cognitive Search)------
        ids = [id for id in raw_data.get("chunk_ids", []) if id.strip()]  # Filter out empty strings
        if ids:
            docid = [{'id': i} for i in ids]
            search_client.delete_documents(documents=docid)
            print("Step 1 finished")

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




@router.get("/getCategories/")
async def get_categories(
        status_flag: Optional[str] = Query(None),
        email: Optional[str] = Query(None)
):
    try:
        category_list = []
        if email is not None:
            query = "SELECT r.categories FROM gi_users r WHERE r.email = @email AND IS_DEFINED(r.categories)"
            query_params = [{"name": "@email", "value": email}]
            query_result = user_container.query_items(
                query=query,
                parameters=query_params,
                enable_cross_partition_query=True
            )

            category_ids = [item["categories"] for item in query_result]
            
            # If there are category IDs, fetch the complete category objects
            if category_ids:
                for category_id in category_ids[0]:
                    query = "SELECT * FROM gi_category r WHERE r.id = @category_id and r.status = 1"
                    query_params = [{"name": "@category_id", "value": category_id}]
                    query_result = category_container.query_items(
                        query=query,
                        parameters=query_params,
                        enable_cross_partition_query=True
                    )
                    # Ensure query_result is a list before concatenation
                    category_list += list(query_result) if query_result else []


        elif status_flag == 1:
            try:
                status_flag = int(status_flag)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status_flag value")

            query = "SELECT * FROM gi_category r WHERE r.status = @status_flag"
            query_params = [{"name": "@status_flag", "value": status_flag}]

            query_result = category_container.query_items(
                query=query,
                parameters=query_params,
                enable_cross_partition_query=True
            )
            category_list = list(query_result)

        else:
            query = "SELECT * FROM gi_category r"
            query_result = category_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            category_list = list(query_result)

        return {"CategoryList": category_list if category_list else []}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/addCategory/")
async def add_category(
    category_code: str = Query(..., alias="category_code"),
    category_name: str = Query(..., alias="category_name"),
):
    try:
        user_name = 'super-admin'
        query = "SELECT * FROM gi_category r WHERE r.category_name = @category_name"
        query_params = [{"name": "@category_name", "value": str(category_name)}]

        # existing_category = db.session.query(gi_category).filter(gi_category.category_name == category_name).first()
        existing_category = None
        query_result = category_container.query_items(
            query=query,
            parameters=query_params,
            enable_cross_partition_query=True
        )

        for item in query_result:
            existing_category = item

        if existing_category is not None:
            return {"message": "Category already exists"}

        # new_category = gi_category(category_code= category_code, category_name=category_name, created_by=user_name, created_at=datetime.now())
        # db.session.add(new_category)
        # db.session.commit()

        category_id = uuid.uuid4()
        item = {
            'id': str(category_id),
            'category_code': category_code,
            'category_name': category_name,
            'created_by': "super-admin",
            'created_at': str(datetime.now()),
            'status': 1
        }
        category_container.create_item(body=item)

        query = f"SELECT * FROM c WHERE c.role = 'Admin'"
        users = list(user_container.query_items(query=query, enable_cross_partition_query=True))

        # Update each user
        for user in users:
            if 'categories' in user:
                if item['id'] not in user['categories']:
                    # Add new category_id if not present
                    user['categories'].append(item['id'])
            else:
                user['categories'] = [item['id']]
            user_container.upsert_item(user)
        return {"message": "Category added successfully"}
    except Exception as e:
        return {"message": "Error occurred while updating category: " + str(e)}




#This API updates the feedback of a previously asked question by ID.
@router.put("/questionFeedback")
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
        qa_record['updatedAt'] = str(datetime.now())
        response = feedback_container.replace_item(item=qa_record, body=qa_record)

        if feedback==1:
            str_id = str(qa_record['id'])
            qna_indexing(str_id,qa_record['question'],qa_record['answer'],qa_record['thoughts'],str(qa_record['data_points']), str(qa_record['exclude_category']), str(qa_record['include_category']))

        return {"message": "Feedback updated successfully for question with ID {}".format(id)}
    except Exception as e:

        return {"message": "Error occurred while updating feedback: " + str(e)}






@router.put("/updateCategory")
async def add_category(
    category_id: str = Query(..., alias="category_id"),
    status_flag: Optional[str] = None,
    category_name: Optional[str] = None,
    category_code: Optional[str] = None,
    ):

    try:
        query = "SELECT * FROM gi_category cat WHERE cat.id = @category_id"
        query_params = [{"name": "@category_id", "value": str(category_id)}]

        # Execute the parameterized query
        categories = category_container.query_items(
            query=query,
            parameters=query_params,
            enable_cross_partition_query=True
        )
        category = next(categories, None)

        if category is None:
            return {"message": "Category not found"}

        status_mapping = {"false": 0, "true": 1}
        category['status'] = status_mapping.get(status_flag, 1)
        if category_name:
            category["category_name"] = category_name
        if category_code:
            category["category_code"] = category_code

        response = category_container.replace_item(item=category, body=category)

        response_message = ""
        if status_flag:
            response_message += "Category Activated." if category['status'] == 1 else "Category Deactivated."
        response_message += "Category is edited." if category_name or category_code  else ""
        return {"message": response_message}

    except Exception as e:
        return {"message": "Error occurred while updating category: " + str(e)}
    
@router.get("/getSharePointData")
async def run_indexer_and_search():
    try:        
        # Run indexer
        result = indexers_client.run_indexer(indexer_name)
        print(f"Ran the Indexer {indexer_name}")
        print()
        
        # Initialize SearchIndexClient to perform search
        search_client = SearchIndexClient(endpoint=azure_search_service_endpoint,
                                         index_name=index_name,
                                         credential=credential)
        
        # Get search client
        search = search_client.get_search_client(index_name=index_name)
        
        # Perform the search
        results = search.search(search_text='*', select=["title"])
        
        # Extract unique titles
        items = set([])
        for result in results:
            items.add(result['title'])
        
        # Return unique titles
        return {"unique_titles": list(items)}
    
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Missing required environment variable: {e}")
    
    except Exception as e:
        # Handle specific exceptions as needed
        print(f"Error running indexer and retrieving SharePoint data: {str(e)}")
        raise HTTPException(status_code=500, detail="Error running indexer and retrieving SharePoint data")
    
  