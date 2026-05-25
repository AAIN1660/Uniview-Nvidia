from utility.blob_storage import get_blob_service_client
from azure.cosmos import CosmosClient, exceptions
import os


cosmos_connection_string = os.environ["COSMOS_CONNECTION_STRING"]
cosmos_client = CosmosClient.from_connection_string(cosmos_connection_string)

COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]

database = cosmos_client.get_database_client(COSMOS_DATABASE_NAME)

user_container_name = "users"
transaction_container_name = "transactions"
config_container_name = "config"
upload_container_name = "uploads"

config_container = database.get_container_client(config_container_name)


def get_blob_container_client():
    container_name = os.getenv("BLOB_STORAGE_CONTAINER_NAME", "unifiedproddocs")
    return get_blob_service_client().get_container_client(container_name)
