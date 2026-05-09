from datetime import datetime, timezone
from http.client import HTTPException
from fastapi import APIRouter, Depends
from azure.cosmos import exceptions, PartitionKey
from azure.storage.blob import BlobServiceClient, PublicAccess
from dotenv import load_dotenv
from utility.helper import *
from azure.core.exceptions import ResourceExistsError
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.storage.queue import QueueServiceClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
	ExhaustiveKnnAlgorithmConfiguration,
	ExhaustiveKnnParameters,
	SearchIndex,
	SearchField,
	SearchFieldDataType,
	SimpleField,
	SearchableField,
	SearchIndex,
	SemanticConfiguration,
	SemanticPrioritizedFields,
	SemanticField,
	SemanticSearch,
	VectorSearch,
	HnswAlgorithmConfiguration,
	HnswParameters,
	VectorSearchAlgorithmKind,
	VectorSearchProfile,
	VectorSearchAlgorithmMetric,
)

router = APIRouter(prefix='/setup', tags=['Setup'])

load_dotenv("unified.env")

# Must match embedding model output size (e.g. 1536 for text-embedding-ada-002, 1024 for nvidia/nv-embedqa-e5-v5).
VECTOR_SEARCH_DIMENSIONS = int(os.getenv("VECTOR_SEARCH_DIMENSIONS", "1536"))

COSMOS_DB_NAME = os.getenv('COSMOS_DATABASE_NAME')
CONFIG_CONTAINER_NAME = os.getenv('CONFIG_CONTAINER_NAME')
CATEGORY_CONTAINER_NAME = os.getenv('CATEGORY_CONTAINER_NAME')
QA_CONTAINER_NAME = os.getenv('QA_CONTAINER_NAME')
UPLOAD_CONTAINER_NAME = os.getenv('UPLOAD_CONTAINER_NAME')
USER_CONTAINER_NAME = os.getenv('USER_CONTAINER_NAME')
TRANSACTION_CONTAINER_NAME = os.getenv('TRANSACTION_CONTAINER_NAME')

AZURE_SEARCH_ENDPOINT = os.getenv('AZURE_SEARCH_SERVICE_ENDPOINT')
AZURE_SEARCH_CREDENTIAL = AzureKeyCredential(os.getenv('AZURE_SEARCH_ADMIN_KEY'))
AZURE_SEARCH_INDEX = os.getenv('AZURE_SEARCH_INDEX_NAME')
AZURE_QNA_INDEX = os.getenv('AZURE_QA_INDEX_NAME')
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")


BLOB_STORAGE_CONTAINER_NAME = os.getenv('BLOB_STORAGE_CONTAINER_NAME')

def _create_container_compat(database, container_id: str):
	"""
	Create container in a way compatible with both provisioned-throughput and
	serverless Cosmos accounts.
	"""
	base_kwargs = {
		"id": container_id,
		"partition_key": PartitionKey(path="/id"),
	}
	try:
		return database.create_container_if_not_exists(
			**base_kwargs,
			offer_throughput=400
		)
	except exceptions.CosmosHttpResponseError as exc:
		msg = str(exc).lower()
		if "serverless" in msg and "throughput" in msg:
			return database.create_container_if_not_exists(**base_kwargs)
		raise


async def create_service():

	# Create Cosmos DB & Containers
	client = get_cosmos_client()
	database = client.create_database_if_not_exists(id=COSMOS_DB_NAME)

	user_container = _create_container_compat(database, USER_CONTAINER_NAME)
	transaction_container = _create_container_compat(database, TRANSACTION_CONTAINER_NAME)
	config_container = _create_container_compat(database, CONFIG_CONTAINER_NAME)
	category_container = _create_container_compat(database, CATEGORY_CONTAINER_NAME)
	qa_container = _create_container_compat(database, QA_CONTAINER_NAME)
	upload_container = _create_container_compat(database, UPLOAD_CONTAINER_NAME)
	db_connection = _create_container_compat(database, "db_connection")
	data_dictionary = _create_container_compat(database, "data_dictionary")

	print("-----COSMOS CONTAINERS CREATED-----")
	await create_superadmin(user_container)
	print("-----SUPER ADMIN CREATED-----")
	await initialize_configuration(config_container)
	print("-----CONFIGURATION INITIALIZED-----")


	# Azure Blob Storage setup
	blob_service_client = BlobServiceClient.from_connection_string(os.getenv("BLOB_STORAGE_CONNECTION_STRING"))

	try:
		container_client = blob_service_client.create_container(BLOB_STORAGE_CONTAINER_NAME,public_access='container')
		print(f"Container {container_name} created.")
	except ResourceExistsError:
		print(f"Container {container_name} already exists.")
	except Exception as e:
		print(f"An error occurred while creating the container {container_name}: {e}")

	print("-----BLOB STORAGE CREATED-----")


	# Azure AI Search Index Setup
	# Configure the vector search configuration
	key = AZURE_SEARCH_ADMIN_KEY
	azure_search_credential = AzureKeyCredential(key)

	vector_search = VectorSearch(
	algorithms=[
		HnswAlgorithmConfiguration(
			name="myHnsw"
		)
	],
	profiles=[
		VectorSearchProfile(
			name="my-vector-config",
			algorithm_configuration_name="myHnsw",
		)
	]
	)

	index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=AZURE_SEARCH_CREDENTIAL)
	fields = [
		SimpleField(name="id", type=SearchFieldDataType.String, key=True, sortable=True, filterable=True, facetable=True, searchable=True,hidden=False),
		SearchableField(name="title", type=SearchFieldDataType.String,sortable=True, filterable=True, facetable=True, searchable=True,hidden=False),
		SearchableField(name="content", type=SearchFieldDataType.String,sortable=True, filterable=True, facetable=True, searchable=True,hidden=False),
		SearchableField(name="category", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True, searchable=True,hidden=False),
		SearchableField(name="sourcepage", type=SearchFieldDataType.String,sortable=True, filterable=True, facetable=True, searchable=True,hidden=False),
		SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), searchable=True,hidden=False, vector_search_dimensions=VECTOR_SEARCH_DIMENSIONS, vector_search_profile_name="my-vector-config")
	]

	semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            keywords_fields=[SemanticField(field_name="category")],
            content_fields=[SemanticField(field_name="content")]
        )
    )
	semantic_settings = SemanticSearch(configurations=[semantic_config])

	# Create the search index with the semantic settings
	index = SearchIndex(name=AZURE_SEARCH_INDEX, fields=fields,vector_search=vector_search, semantic_search=semantic_settings)
	index_client.create_or_update_index(index)
	print('---------- Search Index Created------------------')
 
	#-------- QNA INDEX-----------
	qa_index_client = SearchIndexClient(endpoint=AZURE_SEARCH_SERVICE_ENDPOINT, credential=azure_search_credential)

	qa_fields = [
		SimpleField(name="id", type=SearchFieldDataType.String, key=True),
		SearchableField(name="question", type=SearchFieldDataType.String,searchable=True, hidden=False),
		SearchableField(name="answer", type=SearchFieldDataType.String,searchable=True, hidden=False),
		SearchableField(name="exclude_category", type=SearchFieldDataType.String,filterable=True, searchable=True, hidden=False),
		SearchableField(name="include_category", type=SearchFieldDataType.String,filterable=True, searchable=True, hidden=False),
		SearchableField(name="index_format", type=SearchFieldDataType.String,filterable=True, searchable=True, hidden=False),
		SearchableField(name="tracing", type=SearchFieldDataType.String,filterable=True, searchable=True, hidden=False),
		SearchableField(name="cost_saved", type=SearchFieldDataType.String,filterable=True, searchable=True, hidden=False),
		SearchableField(name="data_points", type=SearchFieldDataType.String,filterable=True, searchable=True, hidden=False),
		SearchableField(name="thoughts", type=SearchFieldDataType.String,filterable=True, searchable=True, hidden=False),
		SearchField(name="contentVector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),searchable=True, vector_search_dimensions=VECTOR_SEARCH_DIMENSIONS, vector_search_profile_name="my-vector-config"),
	]

	qa_semantic_config = SemanticConfiguration(
        name="my-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="answer"),
            content_fields=[SemanticField(field_name="question")]
        )
    )
	# Create the semantic settings with the configuration
	qa_semantic_settings = SemanticSearch(configurations=[qa_semantic_config])

	qa_index = SearchIndex(name=AZURE_QNA_INDEX, fields=qa_fields,vector_search=vector_search, semantic_search=qa_semantic_settings)
	qa_index_client.create_or_update_index(qa_index)


	print('---------- QNA Index Created------------------')


	# Azure Storage Queue setup
	queue_service_client = QueueServiceClient.from_connection_string(os.getenv("BLOB_STORAGE_CONNECTION_STRING"))
	queue_name = os.getenv("AZURE_QUEUE_STORAGE_NAME")

	try:
		queue_client = queue_service_client.create_queue(queue_name)
		print(f"Queue {queue_name} created.")
	except ResourceExistsError:
		print(f"Queue {queue_name} already exists.")
	except Exception as e:
		print(f"An error occurred while creating the queue {queue_name}: {e}")

	print("-----QUEUE STORAGE CREATED-----")




async def create_superadmin(user_container):
	# Initialize config container
	new_user = {
					"id": str(1),
					"numericId":int(1),
					"name": "Super Admin",
					"email": "super_admin@affine.ai",
					"password":encrypt_password(os.getenv('SUPER_ADMIN_PASSWORD')),
					"role": 'superAdmin',
					"credit_balance":500,
					"image_uploaded":0,
					"image_searched":0,
					"tags_generated":0,
					"categories": [],
					"status": 1,
					"jwt_token":None,
					"last_logged_in": None,
					"created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
					"updated_by": None,
					"updated_at": None
				}

	try:
		user_container.create_item(body=new_user)
	except exceptions.CosmosResourceExistsError:
		print("Super Admin already exists.")
	except Exception as e:
		print(f"Error: {e}")


async def initialize_configuration(config_container):
	# Initialize config container
	# config_item_array = [
	# 	{"id": "license","Total_User_License": 10,"Pending_User_License": 10},
	# 	{"id": "creditpool","Use_Credit_Pool": False,"Total_Credit_Pool": 10000,"Balance_Credit_Pool": 10000}
	# ]
	config_item_dict = {
		"id": "configuration",
		"credit_pool_assigned": 10000,
    	"credit_pool_balance": 10000,
    	"total_license": 100,
    	"pending_license": 100,
    	"use_credit_pool": True,
		"search_type": "vector",
		"tokens": 10000,
		"tokens_per_credit": 1000
	}
	# for item in config_item_array:
	try:
		config_container.create_item(body=config_item_dict)
	except exceptions.CosmosResourceExistsError:
		print(f"Config item - {config_item_dict['id']} already exists.")
	except Exception as e:
		print(f"Error: {e}")


@router.put("/update_user_license")
async def update_user_license(total_user_license: int, pending_user_license: int):
	config_container = get_config_container()
	try:
		# Read the existing config item
		config_item = config_container.read_item(item="license", partition_key="license")

		# Update the license counts
		# config_item["Total_User_License"] = total_user_license
		config_item["total_license"] = total_user_license
		# config_item["Pending_User_License"] = pending_user_license
		config_item["pending_license"] = pending_user_license

		# Update the config item in the container
		config_container.replace_item(item=config_item, body=config_item)

		return {"message": "License counts updated successfully"}

	except exceptions.CosmosResourceNotFoundError:
		raise HTTPException(status_code=404, detail="Config item not found")
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Failed to update license counts: {str(e)}")


