from sqlalchemy import create_engine
from sqlalchemy.engine import reflection

from pydantic import BaseModel


from fastapi import Request, HTTPException,Form, status, APIRouter,Query
import urllib
import os
from fastapi.responses import JSONResponse
from azure.cosmos import exceptions
from typing import Optional
import asyncio



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

from utility.cosmos_db import config_container

 

class Config(BaseModel):
    credit_pool_assigned: Optional[int] = None
    credit_pool_balance: Optional[int] = None
    total_license: Optional[int] = None
    pending_license: Optional[int] = None
    use_credit_pool: Optional[bool] = None
    search_type: Optional[str] = None
    tokens: Optional[int] = None
    tokens_per_credit: Optional[int] = None

@router.put("/update_config")
async def update_config(request: Config):
    payload = request
    try:
        query = f"SELECT * FROM c WHERE c.id = 'configuration'"
        config_data_list = list(config_container.query_items(query=query, enable_cross_partition_query=True))

        config_data = config_data_list[0]


        config_data["credit_pool_assigned"] = payload.credit_pool_assigned if payload.credit_pool_assigned else config_data["credit_pool_assigned"]
        config_data["credit_pool_balance"] = payload.credit_pool_balance if payload.credit_pool_balance else config_data["credit_pool_balance"]
        config_data["total_license"] = payload.total_license if payload.total_license else config_data["total_license"]
        config_data["pending_license"] = payload.pending_license if payload.pending_license else config_data["pending_license"]
        config_data["use_credit_pool"] = payload.use_credit_pool if payload.use_credit_pool else config_data["use_credit_pool"]
        config_data["search_type"] = payload.search_type if payload.search_type else config_data["search_type"]
        config_data["tokens"] = payload.tokens if payload.tokens else config_data["tokens"]
        config_data["tokens_per_credit"] = payload.tokens_per_credit if payload.tokens_per_credit else config_data["tokens_per_credit"]


        # Update the config in the container
        config_container.upsert_item(config_data)
        response_data = {"message":"Config data updated successfully","credit_pool_assigned": config_data.get("credit_pool_assigned"), "credit_pool_balance": config_data.get("credit_pool_balance"), "total_license": config_data.get("total_license"), "pending_license": config_data.get("pending_license"), "use_credit_pool": config_data.get("use_credit_pool"), "search_type": config_data.get("search_type"), "tokens": config_data.get("tokens"), "tokens_per_credit": config_data.get("tokens_per_credit")}
        return JSONResponse(content=response_data)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return JSONResponse({"error": cosmos_error.message}, status_code=cosmos_error.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
@router.get("/get_config")
async def get_config(id: str = "configuration"):
    try:
        config_data = []
        if len(id) > 0:
            user_query = f"SELECT * FROM c WHERE c.id = '{id}'"
            config_data = list(config_container.query_items(query=user_query,enable_cross_partition_query=True))
        else:
            config_data = list( config_container.read_all_items())
        response_dict = {
            "config_data": config_data
        }

        return JSONResponse(content=response_dict)
    except exceptions.CosmosHttpResponseError as cosmos_error:
        return JSONResponse({"error": cosmos_error.message}, status_code=cosmos_error.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

