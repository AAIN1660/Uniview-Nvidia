from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, exceptions
import os


cosmos_connection_string = REMOVED_SECRET
# Create a CosmosClientConfiguration instance with the connection string
cosmos_client = CosmosClient.from_connection_string(cosmos_connection_string)

COSMOS_DATABASE_NAME = os.environ["COSMOS_DATABASE_NAME"]
# COSMOS_UPLOAD_CONTAINER = os.environ["COSMOS_UPLOAD_CONTAINER"]
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]

database = cosmos_client.get_database_client(COSMOS_DATABASE_NAME)

# Define your container names here
user_container_name = "users"
transaction_container_name = "transactions"
config_container_name = "config"
upload_container_name = "uploads"

# Define your containers
config_container = database.get_container_client(config_container_name)


def get_blob_container_client():
    connection_string = "DefaultEndpointsProtocol=https;AccountName=quindevv;AccountKey=TCf3G6j7q9Qq4oT85hh0b/mqs+59pyVju710yzSkH7F+ngOLo3+YyQrs/ydsbTuOLV8kkCsx+Eq1+AStaZHcyw==;EndpointSuffix=core.windows.net"
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_name = "quin-dev"
    container_client = blob_service_client.get_container_client(container_name)
    return container_client


def calculate_balance(email, transaction_container):
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
    


def get_inactive_categories():
    # container_users = current_app.config['cosmos_db'].get_container_client("gi_category")
    query = f"SELECT * FROM cat WHERE cat.status = 0"
    cat_list = list(config_container.query_items(query, enable_cross_partition_query=True))
    print("cat list to add in exclude category list:", cat_list)
    return cat_list
