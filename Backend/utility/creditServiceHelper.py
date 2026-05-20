from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from azure.cosmos.container import ContainerProxy
from typing import List
from azure.cosmos import exceptions
from typing import Optional
from pydantic import BaseModel
from azure.cosmos import CosmosClient
import uvicorn
from azure.identity import DefaultAzureCredential
from typing import List, Union, Dict, Any
import os
from datetime import datetime
from azure.cosmos.errors import CosmosHttpResponseError
import uuid
from dotenv import load_dotenv
import asyncio
import traceback
from azure.cosmos import CosmosClient, exceptions
from azure.search.documents import SearchClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient



# Configure environment variables
load_dotenv("unified.env")

def _clean_env(value, default=None):
	value = value if value is not None else default
	if value is None:
		return None
	value = str(value).strip()
	if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
		value = value[1:-1].strip()
	return value

service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
qa_index_name = os.getenv("AZURE_QA_INDEX_NAME")
key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
azure_search_credential = AzureKeyCredential(key)
chunk_size = int(os.environ["chunk_size"])
similar_chunk_count = os.environ["similar_chunk_count"]
k = int(similar_chunk_count)


EMBEDDING_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")


from utility.cosmos_db import (
    config_container,
    transaction_container,
    upload_container,
    user_container,
)

COSMOS_DATABASE_NAME = _clean_env(os.getenv("COSMOS_DATABASE_NAME"))
COSMOS_ENDPOINT = _clean_env(os.getenv("COSMOS_ENDPOINT"))
COSMOS_KEY = _clean_env(os.getenv("COSMOS_KEY"))

user_container_name = _clean_env(os.getenv("USER_CONTAINER_NAME"), "gi_users")
transaction_container_name = _clean_env(os.getenv("TRANSACTION_CONTAINER_NAME"), "transactions")
config_container_name = _clean_env(os.getenv("CONFIG_CONTAINER_NAME"), "config")
upload_container_name = _clean_env(os.getenv("UPLOAD_CONTAINER_NAME"), "gi_uploads")



async def get_current_user_id_from_database():
	query = "SELECT TOP 1 c.id FROM c ORDER BY c.numericId DESC"
	result =  user_container.query_items(query=query, enable_cross_partition_query=True)

	# Check if there are any records
	try:
		last_user = next(result)
		print("last_user",last_user)
		# last_user_numeric = int(last_user['id'])
		return int(last_user['id'])
	except StopIteration:
		# If no records found, return 0 as the starting user ID
		return 0
	except CosmosHttpResponseError as cosmos_error:
		print(f"Error querying Cosmos DB: {cosmos_error}")
		return 0



async def calculate_balance(email, transaction_container):
	try:
		# Fetching data from Cosmos DB transactions table
		query = f"SELECT * FROM transactions t WHERE t.email = '{email}' ORDER BY t.transaction_ts DESC"
		cosmos_transactions = transaction_container.query_items(
			query=query,
			enable_cross_partition_query=True
		)

		transactions = list(cosmos_transactions)

		# Processing Cosmos transactions
		user_credits = [transaction.get('credit', 0) for transaction in transactions]
		sum_debit = sum(transaction.get('debit', 0) for transaction in transactions)

		# Calculating balance
		balance = sum(user_credits) - sum_debit
		round_balance = round(balance, 2)

		return round_balance

	except exceptions.CosmosHttpResponseError as cosmos_error:
		# Handle Cosmos DB errors
		raise cosmos_error
	except Exception as e:
		# Handle other exceptions
		raise e



def check_balance(email):
	balance = calculate_balance(email, transaction_container)
	print("Balance", balance)
	if balance > 0:
		# Continue with the remaining code
		return True
	else:
		# Insufficient balance, return a message
		return False




async def update_transactions_table(email, balance, service_type, token_usage=None, credit_used = 0, credit_assigned = 0):
	if service_type == "expired":
		transaction_type=2
	else:
		transaction_type=1

	#container_transactions = current_app.config['cosmos_db'].get_container_client("transactions")

	try:
		current_trans_id = get_current_trans_id_from_database()
		print(f"current_trans_id: {current_trans_id}")
		current_utc_datetime = datetime.utcnow()
		formatted_datetime = current_utc_datetime.strftime("%Y-%m-%d %H:%M:%S")
		# Add a new entry to transactions table with zero balance for the new user
		new_transaction = {
			"surr_no" : current_trans_id + 1,
			"id": str(uuid.uuid1()),
			"email": email,
			"credit": credit_assigned,
			"balance": balance,
			"debit": credit_used,
			"purchase_type": 1,
			"service_type": service_type,
			"transaction_type": transaction_type,  # Assuming 1 represents a user creation transaction
			"transaction_ts": formatted_datetime
		}
		# Include "token_usage" only if it's provided
		if credit_assigned != 0:
			new_transaction["credit"] = credit_assigned
		if token_usage is not None:
			new_transaction["token_usage"] = token_usage
		if credit_used != 0:
			new_transaction["debit"] = credit_used
		print("New Transaction:", new_transaction)
		transaction_container.create_item(body=new_transaction)

		# Fetch user's role and latest credit balance
		user_info = await get_user_info(email)
		return {"message": "Transaction updated successfully", "role": user_info["role"], "balance": user_info["balance"]}

	except exceptions.CosmosHttpResponseError as cosmos_error:
		print(f"Error updating transactions table: {cosmos_error}")
		return {"message": f"Error updating transactions table: {cosmos_error}"}
	except Exception as e:
		print(f"Error updating transactions table: {str(e)}")
		return {"message": f"Error updating transactions table: {str(e)}"}




def get_current_trans_id_from_database():
	#container_transactions = current_app.config['cosmos_db'].get_container_client("transactions")

	query = "SELECT TOP 1 c.surr_no FROM c ORDER BY c.surr_no DESC"
	result = transaction_container.query_items(query=query, enable_cross_partition_query=True)
	try:
		last_trans_id = next(result)
		return last_trans_id['surr_no']
	except StopIteration:
		return 0
	except exceptions.CosmosHttpResponseError as cosmos_error:
		print(f"Error querying Cosmos DB for transaction ID: {cosmos_error}")
		return 0



def get_config_data():
	# config_container = current_app.config['cosmos_db'].get_container_client("config")
	query = "SELECT * From c"
	result = config_container.query_items(query, enable_cross_partition_query=True)
	config_item = next(iter(result))
	return dict(config_item)



def update_config_data(new_config_data):
	try:
		# config_container = current_app.config['cosmos_db'].get_container_client("config")

		# Assuming you have only one record in the 'config' container
		config_item_iterator = config_container.query_items(
			query="SELECT * FROM c",
			enable_cross_partition_query=True
		)
		config_item = next(config_item_iterator)

		# Update the existing config data with the new values
		#config_item["credit_pool_assigned"] = new_config_data.get("credit_pool_assigned", config_item["credit_pool_assigned"])
		config_item["credit_pool_balance"] = new_config_data.get("credit_pool_balance", config_item["credit_pool_balance"])
		config_item["credit_pool_balance"] = round(config_item["credit_pool_balance"], 2)
		#config_item["use_credit_pool"] = new_config_data.get("use_credit_pool", config_item["use_credit_pool"])

		# Replace the existing config item with the updated one
		config_container.replace_item(item=config_item, body=config_item)

	except Exception as e:
		print(f"Error updating config data: {str(e)}")


def update_pending_license(pending_license):
    try:
        # config_container = current_app.config['cosmos_db'].get_container_client("config")

        # Assuming you have only one record in the 'config' container
        config_item_iterator = config_container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True
        )
        config_item = next(config_item_iterator)

        config_item["pending_license"] = pending_license
        # Replace the existing config item with the updated one
        config_container.replace_item(item=config_item, body=config_item)

    except Exception as e:
        print(f"Error updating config data: {str(e)}")

async def get_user_info(email):
	#container_users = current_app.config['cosmos_db'].get_container_client("gi_users")
	query = f"SELECT TOP 1 c.role, c.id FROM c WHERE c.email = '{email}' ORDER BY c.id DESC"
	result = user_container.query_items(query=query, enable_cross_partition_query=True)

	try:
		user_info = next(result)
		print("userinfo:",user_info)
		balance = await calculate_balance(email,transaction_container)
		return {"role": user_info["role"], "balance": balance}
	except StopIteration:
		return {"role": None, "balance": 0}
	except exceptions.CosmosHttpResponseError as cosmos_error:
		print(f"Error querying Cosmos DB for user info: {cosmos_error}")
		return {"role": None, "balance": 0}

