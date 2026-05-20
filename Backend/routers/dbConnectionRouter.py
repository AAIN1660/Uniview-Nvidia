from sqlalchemy import create_engine, MetaData, Table, select
from sqlalchemy.engine import reflection
from sqlalchemy.orm import sessionmaker
from sqlalchemy.inspection import inspect

from pydantic import BaseModel


from fastapi import Request, HTTPException,Form, status, APIRouter,Query
import urllib
import os
from fastapi.responses import JSONResponse
from azure.cosmos import exceptions
from typing import Optional
import asyncio
from utility.helper import get_tables_list_by_email


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

from utility.cosmos_db import (
    data_dictionary_container,
    db_conn_container,
)

class createDbConnection(BaseModel):
    host:str
    username:str
    password:str
    db_name:str

class updateDbConnection(BaseModel):
    id: str
    host: Optional[str] = ""
    username: Optional[str] = ""
    password: Optional[str] = ""
    db_name: Optional[str] = ""

class updateDataDictionary(BaseModel):
    id: str
    db_connection_id: Optional[str] = ""
    table_name: Optional[str] = ""
    table_desc: Optional[str] = ""
    columns: Optional[list] = []

class getSampleData(BaseModel):
    id: str

async def data_dictionary_service(engine, db_connection_id, table_name):
    try:
        # print("inside data dictionary service")
        inspector = reflection.Inspector.from_engine(engine)
        # # tables = inspector.get_table_names(schema=schema_name)
        # tables = inspector.get_table_names()

        
        # response_data_list = []
        # for table_name in tables:
        columns = inspector.get_columns(table_name)
        # schema = f'schema = "{schema_name}", table_name = "{schema_name}.{table_name}", {table_name}_table = Table(\n'
        columns_data_list = []
        for index, column in enumerate(columns):
            columns_data_list.append({"column_id": index, "column_name": column['name'], "column_type": repr(column['type']), "column_desc": ""})
        print("table_name: ", table_name)
        id = await get_id(data_dictionary_container)
        # print("columns_data_list: ",columns_data_list)
        response_data_dict = {
            "id": str(id),
            "numeric_id": int(id),
            "db_connection_id": db_connection_id,
            "table_name": table_name,
            "table_desc": "",
            "columns": columns_data_list
        }
        data_dictionary_container.upsert_item(body=response_data_dict)
        print(f"Data dictionary service ran successfully creating the response_data_dict: {response_data_dict}")
    except Exception as e:
        return {"message": f"Data dictionary service failed: {e}"}


async def get_id(container):
    query = "SELECT VALUE MAX(c.numeric_id) FROM c"
    results = list(container.query_items(query=query,enable_cross_partition_query=True))
    print(results[0])
    if results:
        max_id = results[0] if results[0] is not None else 0
    else:
        max_id = 0
 
    return max_id + 1

@router.post("/db_conn")
async def check_db_conn_string(request: createDbConnection):
    payload = request
    try:
        connection_string = f'mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(f"DRIVER={driver};SERVER={payload.host};DATABASE={payload.db_name};UID={payload.username};PWD={payload.password}")}'
        engine = create_engine(connection_string)
        inspector = reflection.Inspector.from_engine(engine)
        id = await get_id(db_conn_container)
        print("id: ", id)
        query = f"SELECT * FROM c WHERE c.host = '{payload.host}'"
        existing_connections = list(db_conn_container.query_items(query=query, enable_cross_partition_query=True))

        if existing_connections:
            return {"message": f"DB connection with host {payload.host} already exists"}
        
        new_db_conn = {
            "id": str(id),
            "numeric_id": int(id),
            "host": payload.host,
            "username": payload.username,
            "password": payload.password,
            "db_name": payload.db_name,
            "is_active": True
        }
        db_conn_container.create_item(body=new_db_conn)
        tables = inspector.get_table_names()
        # tasks = [do_http_request(), asyncio.to_thread(fetch_from_db_sync)]
        # results = asyncio.gather(*tasks)
        print("table_list length: ", len(tables))
        for table_name in tables:
            asyncio.create_task(data_dictionary_service(engine, id, table_name))
        return {"message": f"Connection to the {payload.host} for user {payload.username} created successfully.","engine": str(engine)}
    except Exception as e:
        return {"message": f"Connection could not be made due to the following error: {e}"}


@router.get("/get_db_conn_creds")
async def get_db_conn_creds(id: str = ""):
    try:
        db_conn_data = []
        if len(id) > 0:
            user_query = f"SELECT * FROM c WHERE c.id = '{id}'"
            db_conn_data = list(db_conn_container.query_items(query=user_query,enable_cross_partition_query=True))
        else:
            db_conn_data = list( db_conn_container.read_all_items())
        response_dict = {
            "db_conn_data": db_conn_data
        }

        return JSONResponse(content=response_dict)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return JSONResponse({"error": cosmos_error.message}, status_code=cosmos_error.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
@router.get("/get_data_dictionary")
async def get_data_dictionary(db_connection_id: str = ""):
    try:
        db_dictionary_data = []
        if len(db_connection_id) > 0:
            user_query = f"SELECT * FROM c WHERE c.db_connection_id = {db_connection_id}"
            db_dictionary_data = list(data_dictionary_container.query_items(query=user_query,enable_cross_partition_query=True))
        else:
            db_dictionary_data = list( data_dictionary_container.read_all_items())
        response_dict = {
            "db_dictionary_data": db_dictionary_data
        }

        return JSONResponse(content=response_dict)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return JSONResponse({"error": cosmos_error.message}, status_code=cosmos_error.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    

@router.put("/update_db_conn_creds")
async def update_db_conn_creds(request: updateDbConnection):
    try:
        payload = request
        query = f"SELECT * FROM c WHERE c.id = '{payload.id}'"
        existing_connections = list(db_conn_container.query_items(query=query, enable_cross_partition_query=True))

        if not existing_connections:
            return {"message": f"DB connection with id {payload.id} not found", "status": 404}

        existing_connection = existing_connections[0]


        existing_connection["host"] = payload.host if len(payload.host)>0 else existing_connection["host"]
        existing_connection["username"] = payload.username if len(payload.username)>0 else existing_connection["username"]
        existing_connection["password"] = payload.password if len(payload.password)>0 else existing_connection["password"]
        existing_connection["db_name"] = payload.db_name if len(payload.db_name)>0 else existing_connection["db_name"]
        existing_connection["is_active"] = payload.is_active if len(payload.is_active)>0 else existing_connection["is_active"]


        host = existing_connection["host"]
        username = existing_connection["username"]
        password = existing_connection["password"]
        db_name = existing_connection["db_name"]


        try:
            connection_string = f'mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(f"DRIVER={driver};SERVER={host};DATABASE={db_name};UID={username};PWD={password}")}'
            engine = create_engine(connection_string)
        except Exception as e:
            return {"message": f"Error occurred while updating DB connection: DB Connection Credentials invalid"}
        # Update the db connection in the container
        db_conn_container.upsert_item(existing_connection)
        response_data = {"message":"DB Connection updated successfully","host": existing_connection.get("host"), "username": existing_connection.get("username"), "password": existing_connection.get("password"), "db_name": existing_connection.get("db_name"), "is_active": existing_connection.get("is_active")}
        return JSONResponse(content=response_data)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return {"message": f"Error occurred while updating DB connection: {cosmos_error}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unexpected error occurred: {str(e)}")
    

@router.put("/update_data_dictionary")
async def update_data_dictionary(request: updateDataDictionary):
    try:
        payload = request
        query = f"SELECT * FROM c WHERE c.id = '{payload.id}'"
        existing_table_data_list = list(data_dictionary_container.query_items(query=query, enable_cross_partition_query=True))

        if not existing_table_data_list:
            return {"message": f"Table data with id {payload.id} not found", "status": 404}

        existing_table_data = existing_table_data_list[0]


        existing_table_data["db_connection_id"] = int(payload.db_connection_id) if len(payload.db_connection_id)>0 else existing_table_data["db_connection_id"]
        existing_table_data["table_name"] = payload.table_name if len(payload.table_name)>0 else existing_table_data["table_name"]
        existing_table_data["table_desc"] = payload.table_desc if len(payload.table_desc)>0 else existing_table_data["table_desc"]
        existing_table_data["columns"] = payload.columns if len(payload.columns)>0 else existing_table_data["columns"]

        # Update the data in the data dictionary container
        data_dictionary_container.upsert_item(existing_table_data)
        response_data = {"message":"Data dictionary updated successfully","db_connection_id": existing_table_data.get("db_connection_id"), "table_name": existing_table_data.get("table_name"), "table_desc": existing_table_data.get("table_desc"), "columns": existing_table_data.get("columns")}
        return JSONResponse(content=response_data)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return {"message": f"Error occurred while updating Data dictionary: {cosmos_error}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unexpected error occurred: {str(e)}")
    
def get_engine(db_conn):
    host = str(db_conn.get("host", ""))
    db_name = str(db_conn.get("db_name", ""))
    username = str(db_conn.get("username", ""))
    password = str(db_conn.get("password", ""))
    
    odbc_string = "DRIVER={};SERVER={};DATABASE={};UID={};PWD={}".format(
        driver, host, db_name, username, password
    )
    encoded_odbc_string = urllib.parse.quote_plus(odbc_string)
    connection_string = f"mssql+pyodbc:///?odbc_connect={encoded_odbc_string}"
    return create_engine(connection_string)


@router.get("/get_sample_data")
async def get_sample_data(id: str = ""):
    try:
        query = f"SELECT * FROM c WHERE c.id = '{id}'"
        existing_connections = list(db_conn_container.query_items(query=query, enable_cross_partition_query=True))
        if not existing_connections:
            return {"message": "Database connection not found"}
        db_conn = existing_connections[0]
        engine = get_engine(db_conn)

        try:
            with engine.connect() as connection:
                print("✅ Connection successful!")
        except Exception as e:
            print("❌ Connection failed:", e)
            return {"message": f"Database connection failed: {e}"}
        inspector = inspect(engine)
        available_tables = inspector.get_table_names()
        
        metadata = MetaData()
        data_result = {}
        
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            for table_name in available_tables:
                table = Table(table_name, metadata, autoload_with=engine)
                query = select(table).limit(5)  # Fetch only first 5 rows
                result = session.execute(query)
                data_result[table_name] = [dict(row._mapping) for row in result.fetchall()]
        finally:
            session.close()
        
        return data_result
    except Exception as e:
        return {"message": str(e)}
    
    


@router.post("/refresh_db_schema")
async def refresh_db_schema(request: createDbConnection):
    payload = request
    try:
        
        # Fetch all tables (without filtering by db_connection_id) to verify if tables exist
        debug_query = "SELECT * FROM c"
        debug_existing_tables = list(data_dictionary_container.query_items(query=debug_query, enable_cross_partition_query=True))

        print("🔍 Debug: All Tables in Cosmos DB:", [t["table_name"] for t in debug_existing_tables])
        
        # ✅ Fetch existing DB connection
        query = f"SELECT * FROM c WHERE c.host = '{payload.host}'"
        existing_connections = list(db_conn_container.query_items(query=query, enable_cross_partition_query=True))

        if not existing_connections:
            return {"message": f"No existing DB connection found for host {payload.host}"}

        db_connection = existing_connections[0]
        db_connection_id = db_connection["id"]

        # ✅ Connect to Azure SQL Database
        connection_string = f'mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(f"DRIVER={driver};SERVER={payload.host};DATABASE={payload.db_name};UID={payload.username};PWD={payload.password}")}'
        engine = create_engine(connection_string)
        inspector = reflection.Inspector.from_engine(engine)

        # ✅ Fetch new table list from Azure SQL
        new_tables = inspector.get_table_names()
        print("Fetched Tables from Azure SQL:", new_tables)

        # ✅ Fetch existing tables from Cosmos DB (Query by db_connection_id)
        existing_table_query = f"SELECT * FROM c WHERE c.db_connection_id = @db_id"
        existing_tables = list(data_dictionary_container.query_items(
            query=existing_table_query,
            parameters=[{"name": "@db_id", "value": db_connection_id}],
            enable_cross_partition_query=True
        ))

        # ✅ Convert to a dictionary {table_name: table_entry} for fast lookup
        existing_table_dict = {table["table_name"]: table for table in existing_tables}  
        print("Existing Tables in Cosmos DB:", existing_table_dict.keys())  # ✅ Debugging line

        # ✅ Iterate through the new tables
        for table_name in new_tables:
            columns = inspector.get_columns(table_name)
            new_columns_list = [
                {"column_id": idx, "column_name": col["name"], "column_type": repr(col["type"]), "column_desc": ""}
                for idx, col in enumerate(columns)
            ]

            if table_name in existing_table_dict:
                # ✅ Found existing table, update it instead of inserting a new one
                existing_table = existing_table_dict[table_name]
                existing_table_id = existing_table["id"]  # ✅ Get the correct existing ID

                existing_column_names = {col["column_name"] for col in existing_table["columns"]}
                new_column_names = {col["column_name"] for col in new_columns_list}

                if existing_column_names != new_column_names:
                    # ✅ Update the existing document
                    existing_table["columns"] = new_columns_list
                    data_dictionary_container.replace_item(item=existing_table_id, body=existing_table)  
                    print(f"✅ Updated schema for table: {table_name}")
                else:
                    print(f"⚡ No schema change for table: {table_name}")

            else:
                # 🆕 Table does not exist, insert it
                id = await get_id(data_dictionary_container)
                new_table_entry = {
                    "id": str(id),
                    "numeric_id": int(id),
                    "db_connection_id": db_connection_id,
                    "table_name": table_name,
                    "table_desc": "",
                    "columns": new_columns_list
                }
                data_dictionary_container.create_item(body=new_table_entry)  
                print(f"✅ Added new table: {table_name}")

        return {"message": "Database schema refreshed successfully"}

    except Exception as e:
        return {"message": f"Schema refresh failed: {e}"}



@router.get("/get_user_tables")
async def get_user_tables(email: str):
    try:
        user_tables = get_tables_list_by_email(email)
        return JSONResponse(content=user_tables)
    
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
