from azure.storage.blob import BlobServiceClient
from azure.cosmos import exceptions
import os

from utility.cosmos_db import (
    category_container,
    config_container,
    transaction_container,
    upload_container,
    user_container,
)


def get_blob_container_client():
    connection_string = os.environ["BLOB_STORAGE_CONNECTION_STRING"]
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    container_name = os.getenv("BLOB_STORAGE_CONTAINER_NAME", "unifiedproddocs")
    return blob_service_client.get_container_client(container_name)


def calculate_balance(email, transaction_container):
    try:
        query = f"SELECT * FROM transactions t WHERE t.email = '{email}' ORDER BY t.transaction_ts DESC"
        cosmos_transactions = transaction_container.query_items(
            query=query,
            enable_cross_partition_query=True,
        )

        transactions = list(cosmos_transactions)
        user_credits = [transaction.get("credit", 0) for transaction in transactions]
        sum_debit = sum(transaction.get("debit", 0) for transaction in transactions)
        return round(sum(user_credits) - sum_debit, 2)

    except exceptions.CosmosHttpResponseError as cosmos_error:
        raise cosmos_error
    except Exception as e:
        raise e


def get_inactive_categories():
    query = "SELECT * FROM cat WHERE cat.status = 0"
    cat_list = list(
        category_container.query_items(query, enable_cross_partition_query=True)
    )
    print("cat list to add in exclude category list:", cat_list)
    return cat_list
