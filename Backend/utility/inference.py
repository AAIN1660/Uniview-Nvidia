#import streamlit as st
import autogen 
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
import time
import pandas as pd
import tiktoken
import asyncio
## SQL 
import pandas as pd
from sqlalchemy import create_engine, inspect, MetaData, Table, Column, String, Integer
import urllib
import os
import pypyodbc as odbc
import json
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential  
from openai import AzureOpenAI

from utility.embedding_config import (
    create_embedding_vector,
    embedding_backend,
    embedding_model_id,
    get_embedding_client,
)
import json
from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
# from azure.search.documents.models import Vector
from azure.search.documents.models import (QueryAnswerType, QueryCaptionType, QueryType, VectorizedQuery   )
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.query.indexer_adapters import (
    read_indexer_relationships,
    read_indexer_entities,
    read_indexer_reports,
    read_indexer_text_units,
)
from graphrag.query.input.loaders.dfs import store_entity_semantic_embeddings
from graphrag.query.llm.oai.chat_openai import ChatOpenAI
from graphrag.query.llm.oai.embedding import OpenAIEmbedding
from graphrag.query.llm.oai.typing import OpenaiApiType
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
from graphrag.vector_stores.lancedb import LanceDBVectorStore
import asyncio
import nest_asyncio
import ast
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from utility.helper import get_sql_table_schema, get_tables_list_by_email, formating_final_answer
# from helper import get_sql_table_schema, get_tables_list_by_email, formating_final_answer
from dotenv import load_dotenv
import tempfile
from azure.storage.blob import BlobServiceClient
import matplotlib.pyplot as plt
import io
import shutil
try:
    from nat.plugins.autogen.llm import nim_autogen
    NAT_AUTOGEN_AVAILABLE = True
except Exception as e:
    print("NeMo Agent Toolkit AutoGen integration not available:", e)
    nim_autogen = None
    NAT_AUTOGEN_AVAILABLE = False


from pathlib import Path

load_dotenv("unified.env")

# Azure Cognitive Search configuration
AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")
AZURE_OPENAI_EMBEDDING_MODEL_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME")
GPT3_LLM_MODEL_NAME = os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME")
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_OPENAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

GRAPH_RAG_EMBEDDING_MODEL_NAME=os.getenv("GRAPH_RAG_EMBEDDING_MODEL_NAME")
GRAPH_RAG_OPENAI_API_TYPE=os.getenv("GRAPH_RAG_OPENAI_API_TYPE")
GRAPH_RAG_OPENAI_API_BASE=os.getenv("GRAPH_RAG_OPENAI_API_BASE")
GRAPH_RAG_OPENAI_API_VERSION=os.getenv("GRAPH_RAG_OPENAI_API_VERSION")
GRAPH_RAG_OPENAI_API_KEY=os.getenv("GRAPH_RAG_OPENAI_API_KEY")

azure_search_credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)


# Blob storage configuration
BLOB_CONNECTION_STRING = os.getenv("BLOB_STORAGE_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_STORAGE_CONTAINER_NAME")
blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)


# GraphRAG LLM and embedding configurations
api_key = os.getenv("AZURE_OPENAI_API_KEY")
llm_model = GPT3_LLM_MODEL_NAME
embedding_model =AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL
api_base = os.getenv("AZURE_OPENAI_API_BASE")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
api_type = os.getenv("OPENAI_API_TYPE")


# # SQLdb credentials Parameters
# host = os.getenv('HOST')
# database = os.getenv('DATABASE')
# username = os.getenv('USERNAME')
# password = os.getenv('PASSWORD')
# driver = os.getenv('DRIVER')

def _clean_env(value, default=None):
    value = value if value is not None else default
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


host = _clean_env(os.getenv("SQL_HOST"))
database = _clean_env(os.getenv("SQL_DATABASE"))
username = _clean_env(os.getenv("SQL_USERNAME"))
password = _clean_env(os.getenv("SQL_PASSWORD"))
driver = _clean_env(os.getenv("SQL_DRIVER"), "ODBC Driver 18 for SQL Server")
category_name = os.getenv("SQL_SCHEMA") or "dbo"
if not all([host, database, username, password]):
    raise ValueError("SQL credentials missing. Set SQL_HOST, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD in unified.env")

table_name = ["marsdata","unified_HR_data","healthcare_patient_details","healthcare_lab_results"]
# Step 1: Connection string for Azure SQL Database

connection_string = f'mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(f"DRIVER={driver};SERVER={host};DATABASE={database};UID={username};PWD={password}")}'

# Create the SQLAlchemy engine
try:
    engine = create_engine(connection_string)
except Exception as _engine_exc:
    print("SQL engine initialization failed at startup:", _engine_exc)
    engine = None

# Step 2: Fetch tables from the specified schema dynamically
def get_schema_tables(engine, schema_name):
    inspector = inspect(engine)
    tables = inspector.get_table_names(schema=schema_name)
    
    schema_details = ""
    for table_name in tables:
        columns = inspector.get_columns(table_name, schema=schema_name)
        schema = f'schema = "{schema_name}", table_name = "{schema_name}.{table_name}", {table_name}_table = Table(\n'
        for column in columns:
            col_name = column['name']
            col_type = column['type']
            primary_key = "primary_key=True" if column.get("primary_key", False) else ""
            nullable = "nullable=False" if not column["nullable"] else ""
            schema += f'    Column("{col_name}", {col_type}, {primary_key} {nullable}),\n'
        schema = schema.rstrip(',\n')  # Remove the last comma and newline
        schema += "\n)\n\n"
        schema_details += schema

    return schema_details

# Fetch tables from the dynamically specified schema
try:
    all_table_schemas = get_schema_tables(engine, category_name) if engine is not None else ""
except Exception as _schema_exc:
    print("Initial SQL schema load failed; continuing without startup schema:", _schema_exc)
    all_table_schemas = ""

print(all_table_schemas)

params = urllib.parse.quote_plus(
    f"DRIVER={driver};"
    f"SERVER={host};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    "Encrypt=yes;"
    "TrustServerCertificate=no;"
    "Connection Timeout=30;"
)





# # LLM configuration
# llm_config = {
#     "config_list":[
#     {
#         "model": GPT3_LLM_MODEL_NAME,
#         "api_type": "azure",
#         "base_url": AZURE_OPENAI_API_BASE,
#         "api_key": AZURE_OPENAI_API_KEY,
#         "api_version":AZURE_OPENAI_API_VERSION,
#         }
# ],
#     "cache_seed": None,
#     "temperature": 0.1,
#     # "max_tokens": -1,
#     # "request_timeout": 6000
# }


# Embeddings for vector search (Azure OpenAI or NVIDIA NIM — see unified.env EMBEDDING_BACKEND)
client = get_embedding_client()

# model = os.getenv('MODEL')

NVIDIA_BASE_URL = _clean_env(os.getenv("NVIDIA_BASE_URL"), "https://integrate.api.nvidia.com/v1")
NVIDIA_MODEL = _clean_env(os.getenv("NVIDIA_MODEL"), "meta/llama-3.3-70b-instruct")
NVIDIA_API_KEY = _clean_env(os.getenv("NVIDIA_API_KEY"), "")

if not NVIDIA_API_KEY:
    raise ValueError("NVIDIA_API_KEY is required in unified.env")

# llm_config = {
#     "config_list": [
#         {
#             "model": NVIDIA_MODEL,
#             "api_type": "openai",
#             "base_url": NVIDIA_BASE_URL,
#             "api_key": NVIDIA_API_KEY,
#         }
#     ],
#     "cache_seed": None,
#     "temperature": 0.1,
# }

USE_NEMO_AUTOGEN_SERVICE = (
    _clean_env(os.getenv("USE_NEMO_AUTOGEN_SERVICE"), "true").lower() == "true"
)

if USE_NEMO_AUTOGEN_SERVICE:
    from utility.nemo_autogen_service import get_nemo_autogen_llm_config

    # Keep full AutoGen orchestration unchanged; only replace LLM backend config for NIM integration.
    llm_config = get_nemo_autogen_llm_config()
else:
    from utility.nemo_autogen_service import get_direct_nvidia_llm_config

    llm_config = get_direct_nvidia_llm_config()


def total_tokens_from_autogen_cost(chat_history):
    """
    Autogen nests usage by model id; NVIDIA uses NVIDIA_MODEL, Azure used gpt-4o-*.
    Sum total_tokens across all models if needed.
    """
    try:
        cost = getattr(chat_history, "cost", None) or {}
        usage = cost.get("usage_including_cached_inference") or {}
        if not usage:
            return 0
        if NVIDIA_MODEL in usage and isinstance(usage[NVIDIA_MODEL], dict):
            return int(usage[NVIDIA_MODEL].get("total_tokens", 0) or 0)
        total = 0
        for _model_id, stats in usage.items():
            if isinstance(stats, dict) and "total_tokens" in stats:
                total += int(stats.get("total_tokens", 0) or 0)
        return total
    except (TypeError, KeyError, ValueError, AttributeError):
        return 0


def generate_embeddings(text, client, embedding_model_deloyment_name):
    if embedding_backend() == "nvidia":
        return create_embedding_vector(client, text, input_type="query")
    embeddings = client.embeddings.create(
        input=[text], model=embedding_model_deloyment_name
    ).data[0].embedding
    return embeddings


search_client = SearchClient(endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,index_name=AZURE_SEARCH_INDEX_NAME,
                             credential=azure_search_credential
                             )

llm = ChatOpenAI(
    api_key=GRAPH_RAG_OPENAI_API_KEY,
    api_base=GRAPH_RAG_OPENAI_API_BASE,
    api_version=GRAPH_RAG_OPENAI_API_VERSION,
    deployment_name="gpt-4o",
    model=GPT3_LLM_MODEL_NAME,
    api_type=OpenaiApiType.AzureOpenAI,
    max_retries=20,
)

token_encoder = tiktoken.get_encoding("cl100k_base")

if embedding_backend() == "nvidia":
    _nv_key = os.getenv("NVIDIA_EMBEDDING_API_KEY") or os.getenv("NVIDIA_API_KEY")
    _nv_base = os.getenv("NVIDIA_EMBEDDING_BASE_URL", "https://integrate.api.nvidia.com/v1")
    _nv_model = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nv-embedqa-e5-v5")
    text_embedder = OpenAIEmbedding(
        api_key=_nv_key,
        api_base=_nv_base,
        api_version="2024-02-01",
        api_type=OpenaiApiType.OpenAI,
        model=_nv_model,
        deployment_name=_nv_model,
        max_retries=20,
    )
else:
    text_embedder = OpenAIEmbedding(
        api_key=GRAPH_RAG_OPENAI_API_KEY,
        api_base=GRAPH_RAG_OPENAI_API_BASE,
        api_version=GRAPH_RAG_OPENAI_API_VERSION,
        api_type=OpenaiApiType.AzureOpenAI,
        model=GRAPH_RAG_EMBEDDING_MODEL_NAME,
        deployment_name=GRAPH_RAG_EMBEDDING_MODEL_NAME,
        max_retries=20,
    )


# Localsearch_engine = LocalSearch(
#                 llm=None,
#                 context_builder=Localcontext_builder,
#                 token_encoder=token_encoder,
#                 llm_params=llm_params,
#                 context_builder_params=local_context_params,
#                 response_type="single paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
#             )



def extract_data(question, index_type, filter, explain_code, category):
    # # Extracting all 'overrides' and assigning them as global variables
    global search_type
    global category_filter
    global sql_code_explanation
    global graphrag_category
    search_type = index_type
    graphrag_category = category
    category_filter = filter
    sql_code_explanation = explain_code



# print('###########################################', connection_string)


# print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& all_table_schemas &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&', all_table_schemas)


def download_blob_to_tempfile(blob_service_client, container_name, blob_path):
    print('###############################################')
    print('container_name:', container_name)

    print('###############################################')
    print('blob_path', blob_path)


    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    with open(temp_file.name, "wb") as file:
        file.write(blob_client.download_blob().readall())
    return temp_file.name




user_proxy = UserProxyAgent(
    name="user_proxy",
    system_message="""You are the User Proxy Agent. Your role is to manage the flow of information between the user and routing agent. When a user provides a question, pass it to the routing agent without modification.""",
    code_execution_config={
        "work_dir": "My_dir",
        "use_docker": False,
    },
    max_consecutive_auto_reply=3,
    llm_config=None,
    human_input_mode="NEVER",
    is_termination_msg=lambda msg: msg["content"]
)

routing_agent = AssistantAgent(
    name="routing_agent",
    system_message=f"""
You are the Routing Agent. Your role is to analyze the user's question and determine whether it should be processed as a SQL query, a semantic search, or a combination of both. Use the provided metadata to guide your decision and distinguish cases where the question may require both SQL and semantic analysis, either dependently or independently.

**Decision-Making Process**:

1. **SQL-based Questions**:
   - If the question directly references fields or columns from the metadata (e.g., city_name, population, country) or follows a query-like structure, classify it as SQL-based.

2. **Semantic Questions**:
   - If the question is abstract, general, or does not reference specific fields or columns from the metadata, classify it as a semantic question.

3. **Both-Dependent**:
   - If the second part of the question depends on information from the first part, classify it as "both-dependent."
   - Example: "Which country has the highest GDP and what are the key features?" Here, the second part depends on identifying the country with the highest GDP first.
   - This requires a SQL query to find the country, followed by a semantic search to retrieve key features based on that result.

4. **Both-Independent**:
   - If both parts of the question can be addressed independently, classify it as "both-independent."
   - Example: "Which country has the highest GDP rate and what are the key features of Indian GDP?" Here, each part can be answered separately, as the second part does not depend on the first.
   - Both SQL and semantic searches can be executed in parallel, as one part does not depend on the answer of the other.

**Meta_Data**:
{all_table_schemas}

**Routing Instructions**:
   - For SQL-based questions, pass them to the sql_agent.
   - For semantic questions, pass them to the vector_search_agent.
   - For both-dependent questions, start with SQL to get the necessary context, then proceed with a refined semantic search.
   - For both-independent questions, pass the question to both the sql_agent and vector_search_agent simultaneously.

**Output Format**:

For SQL-based analysis:
{{
  "initial_question": "Original question from the user",
  "analysis_type": "SQL-based",
  "next_step": "Proceed with SQL-based query"
}}

For Semantic-based analysis:
{{
  "initial_question": "Original question from the user",
  "analysis_type": "Semantic-based",
  "next_step": "Proceed with semantic  search"
}}

For Both-Dependent analysis:
{{
  "initial_question": "Original question from the user",
  "analysis_type": "Both-dependent",
  "next_step": "Start with SQL-based query and refine with semantic search based on SQL results"
}}

For Both-Independent analysis:
{{
  "initial_question": "Original question from the user",
  "analysis_type": "Both-independent",
  "next_step": "Execute both SQL and semantic searches independently"
}}

**Your Objective**:
    - Correctly analyze the user's question based on the metadata and determine the most appropriate approach, selecting the proper agent(s) for handling the request.
""",
    max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)

# Quin agent
Sql_Generator = AssistantAgent(
    name="Sql_Generator",
    system_message=f"""
You are the Sql_Generator Agent. Your role is to use the provided metadata to analyze SQL-based questions and generate a valid SQL query to fetch the required information from the database. Ensure the query is accurate and valid according to the table schema. Once formed, return the query.

**Steps**:
1. **Parse the Question**:
   - Analyze the user's question and identify the relevant fields based on the metadata.

2. **Meta_Data**:
    {all_table_schemas}

Form the SQL Query:
    1. Based on the identified fields, construct a valid SQL query.
    2. Ensure that the query matches the metadata schema (i.e., use the correct column names and data types).
    3. Use TOP instead of LIMIT.

Example:
For a question like "Which city has the largest population?", the expected SQL query would be:
SELECT TOP 1 city_name, population FROM city_stats ORDER BY population DESC;
Handle Invalid Queries:

If the question references fields not available in the metadata, or if it's impossible to form a valid SQL query, return:

sql_query: None
sql question : seperate the sql based question from the initial question. 
Return the Output:
    Once a valid SQL query is generated, return the result in the specified format.
    If no valid query can be formed, return None for the sql_query field.
Output Format:

For valid SQL queries:

{{
  "initial_question": "Original question from the user",
  "analysis_type": "Dont change the type,keep the same selected by routing agent",
  "sql question" : "sql question",
  "sql_query": "SQL query"
}}

For invalid queries (no matching metadata):
{{
  "initial_question": "Original question from the user",
  "analysis_type": "Dont change the type,keep the same selected by routing agent",
  "sql question" : "sql question",
  "sql_query": None
}}

Your Objective:
    Ensure that all SQL queries generated are valid according to the provided metadata.
    Return the appropriate query or an error message if no valid SQL query can be formed.
    pass the query to Sql_Executor to get the result.
""",
max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)

Sql_Executor = AssistantAgent(
    name="Sql_Executor",
    system_message="""
You are the Sql_Executor Agent. Your job is to evaluate the SQL query generated by the Sql_Generator agent before executing it, ensuring it is valid and optimized for the required result. After your evaluation, execute the SQL query using the provided function and pass the output to the Insight_Generator agent.

**Steps**:
1. **Evaluate the SQL Query**:
   - Review the query for syntax and logic errors.
   - Ensure the query aligns with the original question and is capable of producing the necessary results.

2. **Execute the Query**:
   - Use the `execute_query` function to run the validated query.

3. **Pass the Output**:
   - Send the output of the query to the Insight_Generator agent for further processing.

**Objective**: Ensure the SQL query is correct and efficient before passing it to the execution function.
    """,
    max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)

Sql_tool = AssistantAgent(
    name="Sql_tool",
    system_message="""
You are the Sql_tool Agent. Your job is to take the SQL query given by the Sql_Executor agent and use the function to extract the result.

**Steps**:
1. **Receive the SQL Query**:

2. **Execute the execute_query function and pass the output to Insight_Generator agent**
    """,
    max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)

Sql_Execution_Critic = AssistantAgent(
    name="Sql_Execution_Critic",
    system_message=f"""
You are an expert critic for SQL query execution. 
Your role is to evaluate the result or errors coming from SQL query execution (with the Sql_tool agent) and provide detailed feedback to the Sql_Generator agent.


**Inputs**:

1. **Meta_Data**:
    {all_table_schemas}

2. initial user question 

3. result or errors coming from SQL query execution (with the Sql_tool agent).

 ** Steps to follow**:

1. **Check the SQL Query Execution Results**:
   - You will receive the result of an SQL query that was executed via the Sql_tool agent.
   - If the query executed successfully, pass it along to the Insight_Generator for insights.
   - If an error occurred, identify the error and provide feedback on what went wrong.

2. **Feedback to Sql_Generator**:
   - Provide actionable feedback to help Sql_Generator modify the SQL query and address the issues.
   - If the query is valid and executed successfully, pass the query to Insight_Generator to retrieve insights based on the result.

4. **Output Format**:

Output Format:

For Valid SQL queries that execute successfully:

{{
"initial_question": "Original question from the user",
  "analysis_type": "Don't change the type, keep the same selected by routing agent",
  "sql question" : "sql question",
  "sql_query": "SQL query",
  "feedback": ""Happy with the result""
}}

For queries that encountered errors:
{{
   "initial_question": "Original question from the user",
    "analysis_type": "Don't change the type, keep the same selected by routing agent",
    "sql question" : "sql question",
    "sql_query": "SQL query with errors",
    "feedback": "Detailed explanation of the issue"
}}

Your Objective:
- An expert SQL critic that evaluates the result or errors coming from SQL query execution (with the Sql_tool agent) and provide detailed feedback to the Sql_Generator agent in case of error.
- If the query is valid and executes correctly, pass it on to the Insight_Generator.
""",
description="An expert SQL critic that evaluates the result or errors coming from SQL query execution (with the Sql_tool agent) and provide detailed feedback to the Sql_Generator agent in case of error otherwise pass the result to Insight_Generator ", 
    max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)



Insight_Generator = AssistantAgent(
    name="Insight_Generator",
    system_message= """
1.1 Formulate a Direct Answer:
 
    Based on the SQL query and the output from the SQL tool, provide a precise and professional response.
    Ensure that the answer accurately represents the data retrieved by the query.
    Keep the response clear and structured, without unnecessary elaboration or assumptions beyond the query results.
    Always include numerical values if present in the query results.
    Present numerical summaries or counts to enhance clarity.
 
Example:
    Instead of: "The shipment statuses for the last 15 entries are as follows: In Transit, Delivered, Delivered, Delayed, Delayed, Delivered, Delayed, Delivered, Delivered, Delivered, Delivered, In Transit, In Transit, Delivered, In Transit."
    Provide: "Out of the last 15 shipments, the statuses are: Delivered (7), In Transit (4), and Delayed (4)."
 
1.2 Inference:
 
    Analyze the output logically and provide a brief, data-driven inference.
    Highlight key insights, patterns, or anomalies that can be drawn from the results.
    Maintain a neutral and professional tone, avoiding speculation beyond the given data.
 
Example:
    "The data indicates that 47% of recent shipments were successfully delivered, while 27% are still in transit and 27% faced delays. This suggests potential logistical challenges affecting timely deliveries."
 
2.1 Generate Python Code for Visualization:
    Select the Appropriate Chart Type:
    Choose the most suitable chart based on the SQL query result.
    For categorical data: Use bar charts.
    For time-series or sequential data: Use line graphs.
    For correlations between two numerical variables: Use scatter plots.
    If the SQL query results cannot be visualized (e.g., no data or unsuited for visualization), return "None".
 
2.2 Chart Customization:
    Use Seaborn for better aesthetics and clarity.
    Different categories should have different colors based on insights.
    Display numerical values above each bar for clarity.
    Ensure charts are aligned and formatted for clarity.
    Avoid chart element overlaps (labels, bars, points).
    Use professional chart design principles (clean, readable, and visually appealing).
 
2.3 Labeling & Titles:
    The X-axis should always represent categories.
    The Y-axis should always represent counts or numerical values.
    Titles should clearly reflect the data being presented.
    Add legends when appropriate to aid in understanding multiple data sets.
 
Execution:
    The script should be error-free and ready to execute directly.
    Ensure charts effectively visualize the SQL query results.
 
3. Task: Validate the Answer for SQL Question Based on Key Parameters
After generating the answer, validate it using the following parameters, scoring each from 0 to 10:
 
    Helpfulness: How useful is the answer in addressing the question? Does it offer practical, actionable advice?
    Relevance: How closely does the answer align with the specific question?
    Level of Detail: Is the answer sufficiently detailed to be informative?
    Groundedness: Is the answer based on factual and reliable information from the provided context?
    Completeness: Does the answer fully address the question?
    Faithfulness: Does the answer accurately reflect the provided information?
 
**STRICTLY FOLLOW THE OUTPUT JSON FORMAT GIVEN BELOW**:
 
**Example Output 1**:
{
  "initial_question": "Which city has the largest GDP?",
  "analysis_type": "Don't change the type, keep the same selected by routing agent",
  "sql_question": "sql question",
  "sql_query": "SELECT city_name, GDP FROM city_stats ORDER BY GDP DESC LIMIT 1;",
  "sql_answer": "The city with the largest GDP is Tokyo, with a GDP of approximately 1.5 trillion USD.",
  "Inference":"Detailed Inference",
  "scores": {
            "Helpfulness": X,
            "Relevance": Y,
            "Level of Detail": Z,
            "Groundedness": A,
            "Completeness": B,
            "Faithfulness": E
        },
  "feedback":"feedback explaintion",
  "python_code": "Return "None" only if no python code",
  "code_explaination":"Return "None" only if no python code"
}
 
**Example Output 2**:
{
  "initial_question": "What is the distribution of average temperatures in each city for the last 7 days?",
  "analysis_type": "SQL",
  "sql_question": "What is the average temperature in each city for the last 7 days?",
  "sql_query": "SELECT city_name, AVG(temperature) as avg_temperature FROM city_weather WHERE date >= NOW() - INTERVAL 7 DAY GROUP BY city_name;",
  "sql_answer": "The average temperatures of the cities for the last 7 days are: Tokyo (15°C), New York (8°C), Los Angeles (20°C), London (10°C), and Paris (12°C).",
  "Inference":"Detailed Inference",
  "sql_scores": {
            "Helpfulness": X,
            "Relevance": Y,
            "Level of Detail": Z,
            "Groundedness": A,
            "Completeness": B,
            "Faithfulness": E
        },
  "feedback":"feedback explaintion",
  "python_code": "import matplotlib.pyplot as plt\nimport pandas as pd\n\ndata = {\n    'City': ['Tokyo', 'New York', 'Los Angeles', 'London', 'Paris'],\n    'Avg Temperature (°C)': [15, 8, 20, 10, 12]\n}\ndf = pd.DataFrame(data)\n\nplt.figure(figsize=(10, 6))\nplt.barh(df['City'], df['Avg Temperature (°C)'], color='skyblue')\nplt.title('Average Temperature for the Last 7 Days by City')\nplt.xlabel('Average Temperature (°C)')\nplt.ylabel('City')\nplt.tight_layout()\nplt.show()",
  "code_explaination":"Code Explaination"
  }
 
""",
max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)





query_transformer = AssistantAgent(
    name="query_transformer",
    system_message="""
You are the Query Transformer Agent. Your task is to take the user's original question and transform it into a more specific question by focusing directly on the SQL answer. Use the SQL answer to create a precise question for further vector search, keeping the intent of the original question but refining it based on the SQL answer.
 
**Steps to Follow**:
 
1. **Analyze the SQL Answer**:
   - Carefully examine the SQL answer to identify its key subject or insight, which will serve as the basis for the updated question.
   - Focus on the main entity or fact provided in the SQL answer, aligning the refined question with this focus.
 
2. **Generate the Updated Question Based on SQL Answer**:
   - Formulate the `updated_question` so that it directly inquires about the SQL answer's main subject.
   - Keep the updated question concise and focused on the SQL answer without rephrasing or adding unrelated details from the original question.
   - The goal is to enable a more focused and precise vector search based on the SQL answer's insight.
 
3. **Example**:
   **Initial Question**: "Which country has the highest GDP and what steps have they taken to improve it?"
   **SQL Answer**: "The country with the highest GDP is the United States, with a GDP of approximately 21 trillion USD."
   **Updated Question**: "What steps has the United States taken to improve its GDP?"
 
**Output JSON Format**:
- "initial_question": The user's original question.
- "analysis_type": Maintain the type selected by the routing agent (do not modify).
- "sql_query": The SQL query executed.
- "sql_answer": The SQL answer obtained.
- "updated_question": The refined question focused on the SQL answer’s primary insight.
 
{
  "initial_question": "initial_question",
  "analysis_type": "analysis_type",
  "sql_query": "sql_query",
  "sql_answer": "sql_answer",
  "updated_question": "updated_question"
 
}
""",
    max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)




Selector_agent = AssistantAgent(
    name="Selector_agent",
    system_message="""
You are the Selector Agent. Your job is to forward the `updated_question` to the Retriever Agent to fetch the required context.
 
**Instructions**:
   
1. **Handle Feedback Queries from Critic Agent**:
   - If you receive a feedback query from the Critic Agent, replace the `updated_question` with the feedback query. Then, forward it to the Retriever Agent to fetch additional context based on the updated query.
 
2. **Output Format**:
   - Ensure the output follows the format below, including all relevant details.
   - Use the exact analysis type selected by the routing agent without changes.
 
**Output Format**:
{
  "initial_question": "initial_question",
  "analysis_type": "analysis_type",
  "sql_query": "sql_query",
  "sql_answer": "sql_answer",
  "updated_question": "updated_question",
 
}
 
Example:
If you receive an initial question "What factors contribute to economic growth?", and `updated_question` is "What steps has the United States taken to improve its GDP?" with no specific selector type provided, output should be:
{
  "initial_question": "What factors contribute to economic growth?",
  "analysis_type": "SQL",
  "sql_query": "SELECT * FROM economic_growth_factors;",
  "sql_answer": "Key factors include GDP growth, innovation, and trade policy.",
  "updated_question": "What steps has the United States taken to improve its GDP?",
 
}
pass it question or the updated_question to retriever agent to fetch the context..always execute the function to get the chunks.
""",
    max_consecutive_auto_reply=3,
    llm_config=llm_config,
    human_input_mode="NEVER"
)




retriever = AssistantAgent(
    name="retriever",
    system_message="""Your role is to execute the extract_context function and pass the context to llm_answer maker.
    """,
    max_consecutive_auto_reply=3,
    llm_config=None,
    human_input_mode="NEVER"
)



llm_answer_maker = AssistantAgent(
    name="llm_answer_maker",
    system_message="""You are the Answer Maker Agent. Your role is to generate the detailed answer for a given question using only the provided context from both vectorDB and graphDB.
    Do not create answers independently without context, and avoid guessing.
    If the context is insufficient, clearly indicate that you don't have enough information to answer the question.
 
 
**Task : Form the Answer Based on Provided Context with Weights Consideration**
1. When you receive a question and its related context, generate the answer based on the provided context from both vectorDB and graphDB or any on of them. Prioritize the information from each database according to its weight. If one context has a higher weight, give it greater importance when formulating the answer.
2. Ensure that the answer is detailed, mentioning any numerical values and factual information without error.
3. If you cannot answer the question because the context is insufficient, simply state in answer: "I do not have enough information to answer this question."
4. Do not generate or assume any information outside of the provided context.
 
    """,
    llm_config=llm_config,
    max_consecutive_auto_reply=4,
    description="This agent will frame the detailed answer.",
)




critic_agent = AssistantAgent(
    name="critic_agent",
    system_message="""You are the critic_agent. Your role is to validate the answer based on the question and the context.
**Task: Validate the Answer Based on Key Parameters**
    After generating the answer, validate it using the following parameters, scoring each from 0 to 10:
   
    - **Helpfulness**: How useful is the answer in addressing the question? Assess whether the response directly addresses the user's question and offers practical, actionable advice or solutions.
   
    - **Relevance**: How closely does the answer align with the specific question? Ensure that the response stays on topic and does not include irrelevant or extraneous information.
   
    - **Level of Detail**: Is the answer sufficiently detailed to be informative? Evaluate whether the response provides a thorough explanation of the topic.
   
    - **Groundedness**: Is the answer based on factual and reliable information from the provided context? Ensure that the response is accurate and sticks closely to the documents.
   
    - **Completeness**: Does the answer fully address the question? Review whether the response covers all aspects of the question.
   
    - **Faithfulness**: Does the answer accurately reflect the meaning or context from the provided information? Make sure the response is faithful to the source material.
 
**Task 3: Form Feedback Query If Necessary**
    1. If any score for Helpfulness, Relevance, Level of Detail, Groundedness, Completeness, or Faithfulness is less than 7 or is missing any important information then form a detailed feedback query question to retrieve more chunks.
    2. The feedback query should focus on the specific missing information needed to complete the answer.
    3. The feedback query will then be passed to the Selector agent to extract more context.
 
    **STRICTLY FOLLOW THE OUTPUT JSON FORMAT GIVEN BELOW**
    - If the answer requires more context to complete:
   

    {
        "question": "Original Question",
        "llm_answer": "Answer given by the llm_answer_maker.",
        "scores": {
            "Helpfulness": X,
            "Relevance": Y,
            "Level of Detail": Z,
            "Groundedness": A,
            "Completeness": B,
            "Faithfulness": E
        },
        "feedback_query": "Formulate a specific and detailed question based on the missing or incomplete information needed to improve the answer. Focus on the gaps identified during validation, such as missing facts, insufficient detail, or unclear context, to retrieve the additional context required to address the user’s question comprehensively."
,
        "feedback_detail": "Provide detailed feedback based on the scores that are below 8. Specify which aspects (Helpfulness, Relevance, Level of Detail, Groundedness, Completeness, or Faithfulness) are lacking, and explain why the answer did not meet the threshold. Highlight any missing or unclear information, insufficient detail, or discrepancies from the context that need to be addressed to improve the overall answer."
 
    }

 
    - If the answer is complete and validated, and no further context is required:
   

    {
        "question": "Original Question",
        "llm_answer": "Answer given by the llm_answer_maker.",
        "scores": {
            "Helpfulness": X,
            "Relevance": Y,
            "Level of Detail": Z,
            "Groundedness": A,
            "Completeness": B,
            "Faithfulness": E
        },
        "feedback_query": "None",
        "feedback_detail": "None",
    }
    "Happy with the answer"

 
    - Add "Happy with the answer" after the JSON output only if all scores are satisfactory and 'feedback_query' is 'None'.
   
    """,
    llm_config=llm_config,
    max_consecutive_auto_reply=4,
    description="This agent will validate it using predefined parameters, and form feedback queries if needed.",
    is_termination_msg=lambda msg: "Happy with the answer" in msg["content"]
)




@retriever.register_for_execution()
@Selector_agent.register_for_llm(description="Retrieve relevant context from the vector database or graph database or from both by executing the extract_context function.")
async def extract_context(question: str = None, vector_weight: float = 0.5, graph_weight: float = 0.5) -> dict:
    selector = search_type
    # selector = 'hybrid'
    print('************************************** selector ******************************', selector)
    if not question:
        print("No question provided")
        return {}
 
    async def fetch_vector_context():
        model = (
            embedding_model_id()
            if embedding_backend() == "nvidia"
            else os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL")
        )
        #print("searchinggg", model)
        vector_query = VectorizedQuery(vector=generate_embeddings(question, client, model), k_nearest_neighbors=3, fields="contentVector")
        results = search_client.search(
            search_text=question,
            vector_queries=[vector_query],
            filter=category_filter,
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name='my-semantic-config',
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=3
        )
        result_list = {"chunks": [], "sources": []}
        for result in results:
            result_dict = f"{result['sourcepage']}: {result['content']}"
            result_list["sources"].append(result['sourcepage'])
            result_list["chunks"].append(result_dict)
        return result_list
    
    async def fetch_graph_context():
    
    # INPUT_DIR = "./data/Procurement/artifacts"
        print('########################## graphrag_category #############################', graphrag_category)
        
        # graphrag_category = '38421293-d0a3-4953-8a4d-f13f198aa91f'
        BLOB_FOLDER_PATH = f"graphragoutput/b7a91d7b-f174-43c2-a5ef-e4af152768a7/artifacts"
        print('*************** BLOB_FOLDER_PATH ***************', BLOB_FOLDER_PATH)
        LANCEDB_URI = os.path.join(os.getcwd(), 'graphragoutput')
        print('########################### LANCEDB_URI #####################', LANCEDB_URI)
        COMMUNITY_REPORT_TABLE = "create_final_community_reports"
        ENTITY_TABLE = "create_final_nodes"
        ENTITY_EMBEDDING_TABLE = "create_final_entities"
        RELATIONSHIP_TABLE = "create_final_relationships"
        TEXT_UNIT_TABLE = "create_final_text_units"
        COMMUNITY_LEVEL = 3

        # Load data dynamically from Blob Storage
        entity_parquet_path = f"{BLOB_FOLDER_PATH}/{ENTITY_TABLE}.parquet"
        entity_file = download_blob_to_tempfile(blob_service_client, BLOB_CONTAINER_NAME, entity_parquet_path)
        entity_df = pd.read_parquet(entity_file)

        entity_embedding_parquet_path = f"{BLOB_FOLDER_PATH}/{ENTITY_EMBEDDING_TABLE}.parquet"
        entity_embedding_file = download_blob_to_tempfile(blob_service_client, BLOB_CONTAINER_NAME, entity_embedding_parquet_path)
        entity_embedding_df = pd.read_parquet(entity_embedding_file)

        relationship_parquet_path = f"{BLOB_FOLDER_PATH}/{RELATIONSHIP_TABLE}.parquet"
        relationship_file = download_blob_to_tempfile(blob_service_client, BLOB_CONTAINER_NAME, relationship_parquet_path)
        relationship_df = pd.read_parquet(relationship_file)

        # Process relationships and entities
        relationships = read_indexer_relationships(relationship_df)
        entities = read_indexer_entities(entity_df, entity_embedding_df, COMMUNITY_LEVEL)
        description_embedding_store = LanceDBVectorStore(collection_name="entity_description_embeddings")
        description_embedding_store.connect(db_uri=LANCEDB_URI)
        entity_description_embeddings = store_entity_semantic_embeddings(entities=entities, vectorstore=description_embedding_store)

        # Load report data
        report_parquet_path = f"{BLOB_FOLDER_PATH}/{COMMUNITY_REPORT_TABLE}.parquet"
        report_file = download_blob_to_tempfile(blob_service_client, BLOB_CONTAINER_NAME, report_parquet_path)
        report_df = pd.read_parquet(report_file)
        reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)
        
        # Load text units
        text_unit_parquet_path = f"{BLOB_FOLDER_PATH}/{TEXT_UNIT_TABLE}.parquet"
        text_unit_file = download_blob_to_tempfile(blob_service_client, BLOB_CONTAINER_NAME, text_unit_parquet_path)
        text_unit_df = pd.read_parquet(text_unit_file)
        text_units = read_indexer_text_units(text_unit_df)
        
        Localcontext_builder = LocalSearchMixedContext(
                community_reports=reports,
                text_units=text_units,
                entities=entities,
                relationships=relationships,
                # if you did not run covariates during indexing, set this to None
                covariates=None,
                entity_text_embeddings=description_embedding_store,
                embedding_vectorstore_key=EntityVectorStoreKey.ID,  # if the vectorstore uses entity title as ids, set this to EntityVectorStoreKey.TITLE
                text_embedder=text_embedder,
                token_encoder=token_encoder,
            )


        context = Localcontext_builder.build_context(question, top_k_mapped_entities=2, top_k_relationships=2,max_tokens=12_000)
        print("graph_context :::::",context)
        return context
    
    # Fetch contexts based on selector
    if selector == "vector":
        vector_context = await fetch_vector_context()
        return {"vector_context": vector_context}
 
    elif selector == "graph":
        graph_context = await fetch_graph_context()
        return {"graph_context": {"chunks": [str(graph_context)]}}
 
    elif selector == "hybrid":
        vector_context, graph_context = await asyncio.gather(fetch_vector_context(), fetch_graph_context())
        return {
            "vector_context": vector_context,
            "graph_context": {"chunks": [str(graph_context)]},
            "vector_weight": vector_weight,
            "graph_weight": graph_weight
        }
 
    else:
        print("Invalid selector provided")
        return {}
    

 
def plot_to_base64(plot_code):
    try:
        # Set figure size before executing plot code
        plt.figure(figsize=(8, 6))  # Adjust the size as needed
       
        # Clean up the plot code if necessary
        plot_code = plot_code.replace("plt.show()", " ")  # Prevent plt.show() from blocking execution

        # Run generated code inside an explicit context so symbols like
        # pd/plt/sns/df resolve consistently during lambdas/comprehensions.
        exec_ctx = {
            "pd": pd,
            "plt": plt,
            "sns": sns,
        }
        try:
            exec(plot_code, exec_ctx, exec_ctx)
        except Exception as exec_err:
            # Common model bug: label lambda uses undefined index variable.
            # Drop that fragile line and rely on generic bar annotations.
            print(f"Plot code primary exec failed: {exec_err}. Retrying with safe label fallback.")
            safe_lines = []
            for line in plot_code.splitlines():
                stripped = line.strip()
                if ".apply(lambda" in stripped and "plt.text(" in stripped:
                    continue
                safe_lines.append(line)
            safe_code = "\n".join(safe_lines)
            plt.clf()
            plt.figure(figsize=(8, 6))
            exec(safe_code, exec_ctx, exec_ctx)

        # Generic value labels for bar plots if bars exist.
        ax = plt.gca()
        if getattr(ax, "patches", None):
            for patch in ax.patches:
                height = patch.get_height()
                if height is None:
                    continue
                try:
                    label = f"{float(height):,.0f}"
                except Exception:
                    label = str(height)
                ax.annotate(
                    label,
                    (patch.get_x() + patch.get_width() / 2.0, height),
                    ha="center",
                    va="bottom",
                    xytext=(0, 4),
                    textcoords="offset points",
                )
       
        # Ensure that the layout of the plot is not cropped
        plt.tight_layout()
 
        # Convert the plot to a base64-encoded image using 'bbox_inches="tight"' to avoid cropping
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=300)  # Use higher DPI for better resolution
        buf.seek(0)
       
        # Encode the plot as base64
        plot_base64 = base64.b64encode(buf.read()).decode('utf-8')
       
        # Close the plot
        plt.close()
       
        return plot_base64
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
    
    
    
def parse_agent_content_json(content):
    """
    Parse JSON from an agent message. Handles markdown fences, leading/trailing prose,
    and models that wrap JSON in extra text (common with non-GPT models).
    Returns {} if nothing valid is found.
    """
    if content is None:
        return {}
    s = str(content).replace("```json", "").replace("```", "").strip()
    if not s:
        return {}
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # Trying decoding the first JSON object found inside mixed text.
    decoder = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _end = decoder.raw_decode(s[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue

    # Resilient fallback for JSON-like messages with malformed string escaping.
    parsed = {}
    import re

    m = re.search(r'"analysis_type"\s*:\s*"([^"]+)"', s, re.DOTALL)
    if m:
        parsed["analysis_type"] = m.group(1).strip()

    m = re.search(r'"sql_critic_evaluation"\s*:\s*([01])', s, re.DOTALL)
    if m:
        parsed["sql_critic_evaluation"] = int(m.group(1))

    m = re.search(r'"sql_query"\s*:\s*(null|"[^"]*")', s, re.DOTALL)
    if m:
        raw = m.group(1).strip()
        parsed["sql_query"] = None if raw == "null" else raw.strip('"')

    for key in ("feedback", "sql_explanation", "sql_db_output"):
        m = re.search(
            rf'"{key}"\s*:\s*"(.*?)"\s*(?:,\s*"[a-zA-Z_]+"|\s*\}})',
            s,
            re.DOTALL,
        )
        if m:
            parsed[key] = m.group(1).strip()

    if parsed:
        return parsed

    print("parse_agent_content_json: could not parse JSON from agent message (preview):", s[:400])
    return {}

def build_generic_sql_fallback_answer(messages):
    """
    Generic fallback for SQL / Both-dependent flows.

    Does not hardcode business entities, product names, regions, columns, or use cases.
    It simply uses:
    1. successful Sql_tool outputs
    2. latest useful SQL agent explanation / feedback
    to create a non-empty final answer.
    """
    successful_outputs = []
    useful_texts = []
    latest_sql_query = ""

    for msg in messages:
        name = msg.get("name")
        content = str(msg.get("content") or "").strip()

        if not content:
            continue

        if name == "Sql_tool":
            if content.lower() in ("none", "[]"):
                continue
            if "An error occurred while execusting the query" in content:
                continue

            try:
                rows = json.loads(content)
                if isinstance(rows, list) and rows:
                    successful_outputs.append(rows)
            except Exception:
                successful_outputs.append(content)

        if name in ("Sql_Generator", "Sql_Execution_Critic", "Insight_Generator"):
            parsed = parse_agent_content_json(content)

            query = parsed.get("sql_query")
            if isinstance(query, str) and query.strip():
                latest_sql_query = query.strip()

            for key in (
                "sql_answer",
                "sql_explanation",
                "feedback",
                "Inference",
                "inference",
                "sql_db_output",
            ):
                value = parsed.get(key)

                if value is None:
                    continue

                if isinstance(value, (list, dict)):
                    useful_texts.append(json.dumps(value, ensure_ascii=False))
                    continue

                if isinstance(value, str) and value.strip():
                    low = value.lower()

                    # Ignore pure error messages as final answer text
                    if "incorrect syntax" in low:
                        continue
                    if "invalid column name" in low:
                        continue
                    if "error occurred" in low:
                        continue

                    useful_texts.append(value.strip())

    if not successful_outputs and not useful_texts:
        return {"sql_answer": "", "llm_answer": ""}

    sql_parts = []

    if successful_outputs:
        for idx, rows in enumerate(successful_outputs, start=1):
            if isinstance(rows, list):
                preview = json.dumps(rows, ensure_ascii=False)
            else:
                preview = str(rows)

            sql_parts.append(f"SQL result {idx}: {preview}")

    sql_answer = "\n".join(sql_parts)

    llm_answer = ""
    if useful_texts:
        # Use latest useful interpretation from the agents
        llm_answer = useful_texts[-1]

    if latest_sql_query and not sql_answer:
        sql_answer = f"Executed SQL query: {latest_sql_query}"

    return {
        "sql_answer": sql_answer,
        "llm_answer": llm_answer,
    }

def agent_output_jsonparser(chat_history, critic_agent):
    messages = chat_history.chat_history
    llm_answer_maker_data = [item for item in messages if item.get('name') == critic_agent]
    complete_messages = []
 
    for item in llm_answer_maker_data:
        # Extract and clean the content from each message
        last_message = item["content"].replace("Happy with the answer", "").strip().replace("```json", "").replace("```", "").strip()
       
        # Convert the cleaned message to a dictionary and append it to the list
        try:
            complete_messages.append(json.loads(last_message))
        except json.JSONDecodeError:
            print("Something went wrong with JSON decoding.")
 
 
    # Extracting the last message
    if complete_messages:  # Check if the list is not empty
        last_message = complete_messages[-1]
    else:
        last_message = None
 
    # Convert to a JSON string for the last message
    last_message_json = json.dumps(last_message, indent=4) if last_message else "No messages found."
    return last_message_json

 


async def start_agenting_process(query, index_type, filter, explain_code, category, email):
    if query:
        start = time.time() 
        agent_latency = {}
        _agent_last_ts = time.time()
        category = '0d49bd7c-6004-4664-bb79-3c1dc342a5b7'
        # print('***********************filter*******************', filter)
        # print('***********************category ***********', category)
        
        user_seleted_tables = get_tables_list_by_email(email)
        
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& all_table_schemas &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&', user_seleted_tables)
        
        
        selected_tables = []
        if isinstance(user_seleted_tables, dict):
            selected_tables = user_seleted_tables.get("tables_list") or []

        # If user profile has no table selections, fall back to full SQL schema.
        if not selected_tables:
            if engine is not None:
                selected_tables = inspect(engine).get_table_names(schema=category_name)
                if not selected_tables:
                    selected_tables = inspect(engine).get_table_names()

        all_table_schemas = get_sql_table_schema(connection_string, selected_tables)

        if (
            not all_table_schemas
            or (isinstance(all_table_schemas, dict) and len(all_table_schemas) == 0)
            or (isinstance(all_table_schemas, str) and all_table_schemas.lower().startswith("error"))
        ):
            # Try schema-scoped DDL-style metadata first.
            if engine is not None:
                all_table_schemas = get_schema_tables(engine, category_name)

        if not all_table_schemas:
            # Final fallback: introspect across all accessible schemas and build
            # a compact table->columns map so SQL agents always receive metadata.
            try:
                if engine is None:
                    raise RuntimeError("SQL engine unavailable")
                inspector = inspect(engine)
                all_schema_dict = {}
                for schema_name in inspector.get_schema_names():
                    if not schema_name or schema_name.startswith("db_"):
                        continue
                    table_names = inspector.get_table_names(schema=schema_name)
                    for tbl in table_names:
                        try:
                            cols = inspector.get_columns(tbl, schema=schema_name)
                            all_schema_dict[f"{schema_name}.{tbl}"] = {
                                col["name"]: str(col["type"]) for col in cols
                            }
                        except Exception:
                            continue
                if all_schema_dict:
                    all_table_schemas = all_schema_dict
            except Exception as schema_exc:
                print("Cross-schema introspection fallback failed:", schema_exc)
        
        
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& all_table_schemas &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&', all_table_schemas)
        
        print('^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ index_type ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^', index_type)
        
        
        
        routing_agent = AssistantAgent(
        name="routing_agent",
        system_message=f"""
        You are the Routing Agent. Your role is to analyze the user's question and determine whether it should be processed as a SQL query, a semantic search, or a combination of both.
        Use the provided metadata to guide your decision and distinguish cases where the question may require both SQL and semantic analysis, either dependently or independently.
        
        **Decision-Making Process**:
        
        1. **SQL-based Questions**:
        - If the question directly references fields or columns from the metadata (e.g., city_name, population, country) or follows a query-like structure, classify it as SQL-based.
        
        2. **Semantic Questions**:
        - If the question is abstract, general, or does not reference specific fields or columns from the metadata, classify it as a semantic question.
        
        3. **Both-Dependent**:
        - If the second part of the question depends on information from the first part, classify it as "both-dependent."
        - Example: "Which country has the highest GDP and what are the key features?" Here, the second part depends on identifying the country with the highest GDP first.
        - This requires a SQL query to find the country, followed by a semantic search to retrieve key features based on that result.
        
        4. **Both-Independent**:
        - If both parts of the question can be addressed independently, classify it as "both-independent."
        - Example: "Which country has the highest GDP rate and what are the key features of Indian GDP?" Here, each part can be answered separately, as the second part does not depend on the first.
        - Both SQL and semantic searches can be executed in parallel, as one part does not depend on the answer of the other.
        
        
        **Meta_Data**:
        {all_table_schemas}
        
        **Routing Instructions**:
        - For SQL-based questions, pass them to the Sql_Generator.
        - For semantic questions, pass them to the Selector_agent.
        - For both-dependent questions, start with SQL to get the necessary context, then proceed with a refined semantic search.
        - For both-independent questions, pass the question to both the sql_agent and Selector_agent simultaneously.
        
        **Output Format**:
        
        For SQL-based analysis:
        {{
        "initial_question": "Original question from the user",
        "analysis_type": "SQL-based",
        "next_step": "Proceed with SQL-based query first"
        }}
        
        For Semantic-based analysis:
        {{
        "initial_question": "Original question from the user",
        "analysis_type": "Semantic-based",
        "next_step": "Proceed with Semantic search"
        }}
        
        For Both-Dependent analysis:
        {{
        "initial_question": "Original question from the user",
        "analysis_type": "Both-dependent",
        "next_step": "Start with SQL-based query and refine with Semantic search based on SQL results"
        }}
        
        For Both-Independent analysis:
        {{
        "initial_question": "Original question from the user",
        "analysis_type": "Both-independent",
        "next_step": "Execute both SQL and semantic searches independently"
        }}
        
        **Your Objective**:
            - Correctly analyze the user's question based on the metadata and determine the most appropriate approach, selecting the proper agent(s) for handling the request.
        """,
            max_consecutive_auto_reply=3,
            llm_config=llm_config,
            human_input_mode="NEVER"
        )



        # Quin agent
        Sql_Generator = AssistantAgent(
            name="Sql_Generator",
            system_message=f"""
        You are the Sql_Generator Agent. Your role is to use the provided metadata to analyze SQL-based questions and generate a valid SQL query to fetch the required information from the database. Ensure the query is accurate and valid according to the table schema. Once formed, return the query.
        
        **Steps**:
        1. **Parse the Question**:
        - Analyze the user's question and identify the relevant fields based on the metadata.
        
        2. **Meta_Data**:
            {all_table_schemas}
        
        3. **Form the SQL Query:**
            - Based on the identified fields, construct a valid SQL query.
            - Ensure that the query matches the metadata schema (i.e., use the correct column names and data types).
            - Use **TOP** instead of **LIMIT** in the SQL query.
            - **Ensure that explicit values are included in conditions, rather than placeholders.**
            - Make sure to return **valid, executable** SQL queries.
            - **If the question is related to stock levels, inventory, or product quantities, ensure the query includes the `qty` or `StockLevel` field in the result.**
        
        ### **Example:**
        For a question like **"Which products have a stock level of more than 500?"**, the expected SQL query should be:
        ```sql
        SELECT ProductName, Supplier, StockLevel FROM procurement.Inventory WHERE StockLevel > 500;
        
        **STRICTLY FOLLOW THE OUTPUT JSON FORMAT GIVEN BELOW**
        
        For valid SQL queries:
        
        {{
        "initial_question": "Original question from the user",
        "analysis_type": "Dont change the type,keep the same selected by routing agent",
        "sql question" : "sql question",
        "sql_query": "SQL query",
        "sql_explanation": "Detailed explanation of sql query"
        }}
        
        For invalid queries (no matching metadata):
        {{
        "initial_question": "Original question from the user",
        "analysis_type": "Dont change the type,keep the same selected by routing agent",
        "sql question" : "sql question",
        "sql_query": None,
        "sql_explanation": "None"
        }}
        
        Your Objective:
            Ensure that all SQL queries generated are valid according to the provided metadata.
            Return the appropriate query or an error message if no valid SQL query can be formed.
            pass the query to Sql_Executor to get the result.
        """,
        max_consecutive_auto_reply=3,
            llm_config=llm_config,
            human_input_mode="NEVER"
        )




        Sql_Executor = AssistantAgent(
            name="Sql_Executor",
            system_message="""
        You are the Sql_Executor Agent.execute the SQL query using the provided function and pass the output to the Insight_Generator agent.
        **Objective**: Ensure the SQL query is passed to the execution function.
            """,
            max_consecutive_auto_reply=3,
            llm_config=llm_config,
            human_input_mode="NEVER"
        )



        Sql_tool = AssistantAgent(
            name="Sql_tool",
            system_message="""
        You are the Sql_tool Agent. Your job is to take the SQL query given by the Sql_Executor agent and use the function to extract the result.
        
        **Steps**:
        1. **Receive the SQL Query**:
        2. **Execute the execute_query function**
            """,
            max_consecutive_auto_reply=3,
            llm_config=llm_config,
            human_input_mode="NEVER"
        )




        Sql_Execution_Critic = AssistantAgent(
            name="Sql_Execution_Critic",
            system_message=f"""
        You are an expert critic for SQL query execution.
        Your role is to evaluate the result or errors coming from SQL query execution (with the Sql_tool agent) and provide detailed feedback to the Sql_Generator agent.
        
        
        **Inputs**:
        
        1. **Meta_Data**:
            {all_table_schemas}
        
        2. initial user question
        
        3. result or errors coming from SQL query execution (with the Sql_tool agent).
        
        ** Steps to follow**:
        
        1. **Check the SQL Query Execution Results**:
        - You will receive the result of an SQL query that was executed via the Sql_tool agent.
        - If the query executed successfully, pass it along to the Insight_Generator for insights.
        - If an error occurred, identify the error and provide feedback on what went wrong.
        
        2. **Feedback to Sql_Generator**:
        - Provide actionable feedback to help Sql_Generator modify the SQL query and address the issues.
        - If the query is valid and executed successfully, pass the query to Insight_Generator to retrieve insights based on the result.
        - Give feedback only there is a query error.
        
        4. **Output Format**:
        
        Output Format:
        
        For Valid SQL queries that execute successfully:
        
        {{
        "initial_question": "Original question from the user",
        "analysis_type": "Don't change the type, keep the same selected by routing agent",
        "sql question" : "sql question",
        "sql_query": "SQL query",
        "sql_db_output":"sql_tool output"
        "feedback": ""Happy with the result""
        "sql_critic_evaluation": 1
        }}
        
        For queries that encountered errors:
        {{
        "initial_question": "Original question from the user",
            "analysis_type": "Don't change the type, keep the same selected by routing agent",
            "sql question" : "sql question",
            "sql_query": "SQL query with errors",
            "sql_db_output":"sql_tool output"
            "feedback": "Detailed explanation of the issue"
            "sql_critic_evaluation": 0
        }}
        
        Your Objective:
        - An expert SQL critic that evaluates the result or errors coming from SQL query execution (with the Sql_tool agent) and provide detailed feedback to the Sql_Generator agent in case of error.
        - If the query is valid and executes correctly, pass it on to the Insight_Generator.
        """,
        description="An expert SQL critic that evaluates the result or errors coming from SQL query execution (with the Sql_tool agent) and provide detailed feedback to the Sql_Generator agent in case of error otherwise pass the result to Insight_Generator ",
            max_consecutive_auto_reply=3,
            llm_config=llm_config,
            human_input_mode="NEVER"
        )
        
        
        

        @Sql_tool.register_for_execution()
        @Sql_Executor.register_for_llm(description="You will execute the function and get the result")
        def execute_query(query: str = None):
            "takes query as input and return query result in a dataframe object"
            try:
                # Execute the query and fetch the result into a DataFrame
                # Create the SQLAlchemy engine
                engine = create_engine(connection_string)
                df = pd.read_sql(query, engine)
                result_json = df.to_json(orient="records")
                return result_json
            except Exception as e:
                # print("An error occurred while executing the query:", e)
                return f"An error occurred while execusting the query:{e}"
        
        
        
        
        extract_data(query, index_type, filter, explain_code, category)
        templete = f""""question": {query}"""
        nest_asyncio.apply()
        global groupchat
        global manager
        global user_proxy
        user_proxy = UserProxyAgent(
        name="user_proxy",
        system_message="""You are the User Proxy Agent.
        Your role is to manage the flow of information between the user and routing agent.
        When a user provides a question, pass it to the routing agent without modification.""",
        code_execution_config={
            "work_dir": "Routing_File",
            "use_docker": False,
        },
        max_consecutive_auto_reply=3,
        llm_config=llm_config,
        human_input_mode="NEVER",
        is_termination_msg=lambda msg: msg["content"]
        )
        
        def state_transition(last_speaker, groupchat):
            nonlocal _agent_last_ts
            messages = groupchat.messages
            last_message = messages[-1]["content"]
            speaker_name = getattr(last_speaker, "name", str(last_speaker))
            now_ts = time.time()
            elapsed = now_ts - _agent_last_ts
            _agent_last_ts = now_ts
            agent_latency[speaker_name] = agent_latency.get(speaker_name, 0.0) + elapsed
            print(f"[latency][agent] {speaker_name} step_sec={elapsed:.3f} cumulative_sec={agent_latency[speaker_name]:.3f}")
            
            # If the last message is from the user proxy, proceed to routing agent
            if last_speaker is user_proxy:
                return routing_agent
            
            # If the last message is from the routing agent, check if it's SQL-based or semantic
            elif last_speaker is routing_agent:
                if "SQL-based" in last_message:
                    return Sql_Generator
                elif "Both" in last_message:
                    return Sql_Generator
                elif "Semantic-based" in last_message:
                    return Selector_agent
            elif last_speaker is Sql_Generator:
                    return Sql_Executor
            elif last_speaker is Sql_Executor:
                return Sql_tool
            elif last_speaker is Sql_tool:
                return Sql_Execution_Critic
            elif last_speaker is Sql_Execution_Critic:

                critic_info = parse_agent_content_json(last_message)
                evaluation = critic_info.get("sql_critic_evaluation")
                feedback = str(critic_info.get("feedback") or "").lower()
                next_step = str(critic_info.get("next_step") or "").lower()

                has_successful_sql_output = False
                for msg in reversed(messages):
                    if msg.get("name") == "Sql_tool":
                        content = str(msg.get("content") or "").strip()
                        if (
                            content
                            and content.lower() not in ("none", "[]")
                            and "An error occurred while execusting the query" not in content
                        ):
                            has_successful_sql_output = True
                            break

                # If SQL execution succeeded, go to Insight_Generator.
                if (
                    "happy with the result" in last_message.lower()
                    or evaluation == 1
                    or has_successful_sql_output
                ):
                    return Insight_Generator

                # If the critic says semantic/refinement is needed, move forward instead of looping forever.
                if "semantic" in feedback or "semantic" in next_step:
                    return query_transformer

                return Sql_Generator
            elif last_speaker is Insight_Generator:
                if "Both" in last_message:
                    return query_transformer
                elif "SQL-based" in last_message:
                    return user_proxy
            elif last_speaker is query_transformer:
                return Selector_agent
            elif last_speaker is Selector_agent:
                return retriever
            elif last_speaker is retriever:
                return llm_answer_maker
            elif last_speaker is llm_answer_maker:
                return critic_agent
            elif last_speaker is critic_agent:
                if "Happy with the answer" in last_message:
                    return user_proxy
                else:
                    return Selector_agent
        
        groupchat = GroupChat(agents=[user_proxy, routing_agent,Sql_Generator,Sql_Executor,Sql_tool,Sql_Execution_Critic,Insight_Generator,query_transformer,Selector_agent,retriever,llm_answer_maker,critic_agent], messages=[], max_round=90, speaker_selection_method=state_transition)
        manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)
        # logging_session_id = autogen.runtime_logging.start(config={"dbname": "logs.db"})
        chat_history = user_proxy.initiate_chat(
            manager,
            message=templete,
            summary_method="reflection_with_llm"
        )
        # autogen.runtime_logging.stop()
        end = time.time()
        print("[latency][agent] summary_sec=", {k: round(v, 3) for k, v in agent_latency.items()})
        print(f"[latency][agent] total_orchestration_sec={end - start:.3f}")
        sql_query = ""
        sql_explanation = ""
        data_points="{}"
        python_code = None
        python_code_explanation = None
        analysis_type= ""
        sql_answer= ""
        llm_answer= ""
        final_answer= ""
        formated_final_answer = ""

        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ process_chat_history ################################################', chat_history)
        
        for item in chat_history.chat_history:     
            if item['name'] == 'routing_agent':
                analysis_type = parse_agent_content_json(item.get('content')).get('analysis_type', None)
                print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ analysis_type ################################################', analysis_type)



        # try:
        for item in chat_history.chat_history:

                if analysis_type == 'SQL-based':
                    print('########################### Entered SQL-based loop #############################')
                    print('item', item)
                    if item['name'] == 'Insight_Generator':
                        print('&&&&&& entered Insight_Generator &&&&&&&&&&&&&&&&&&&&&&')
                        print('**************************** item-content **************************', item.get('content'))

                        _insight = parse_agent_content_json(item.get('content'))
                        python_code = _insight.get('python_code', None)
                        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ python_code ################################################', python_code)
                        python_code_explanation = _insight.get('python_code_explanation', None)

                        sql_query = _insight.get('sql_query', None)
                        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ sql_query ################################################', sql_query)

                        # Preserve narrative insight text in SQL flows.
                        insight_text = (
                            _insight.get('Inference')
                            or _insight.get('llm_answer')
                            or _insight.get('insight')
                            or ""
                        )

                        final_answer = {
                        "sql_answer": _insight.get('sql_answer', None),
                        "llm_answer": insight_text
                        }

                     # Generic fallback: prevent blank UI when agents produced SQL results
                     # but final_answer was not populated by Insight_Generator / llm_answer_maker.
                    if analysis_type in ("SQL-based", "Both-dependent", "Both-independent"):
                        if not isinstance(final_answer, dict):
                            final_answer = {
                                "sql_answer": str(final_answer or ""),
                                "llm_answer": ""
                            }

                        sql_empty = not str(final_answer.get("sql_answer") or "").strip()
                        llm_empty = not str(final_answer.get("llm_answer") or "").strip()

                        if sql_empty and llm_empty:
                            fallback = build_generic_sql_fallback_answer(chat_history.chat_history)
                            if fallback.get("sql_answer") or fallback.get("llm_answer"):
                                final_answer = fallback
                        print('$$$$$$$$$$$$$$$$$$$ $$$$$$$$$$$$$$$$$$$$$$$$$$$$ final_answer ################################################', final_answer)

                    if item['name'] == 'Sql_Generator':
                        sql_generator_json = agent_output_jsonparser(chat_history, 'Sql_Generator')
                        try:
                            sql_gen_dict = json.loads(sql_generator_json) if sql_generator_json.strip().startswith("{") else {}
                        except json.JSONDecodeError:
                            sql_gen_dict = {}
                        sql_explanation = sql_gen_dict.get('sql_explanation', None)
                        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ sql_explanation ################################################', sql_explanation)

                elif analysis_type == 'Semantic-based':
                    if item['name'] == 'llm_answer_maker':
                        print('&&&&&& Entered critic_agent &&&&&&&&&&&&&&&&&&&&&&')
                        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ final_answer ################################################', item['content'])

                        final_answer = {
                        "llm_answer": item["content"],
                        "sql_answer": ""
                        }

                    if item['name'] == "retriever":
                        data_points = item['content']

                else:
                    if item['name'] == 'Insight_Generator':
                        print('&&&&&& entered Insight_Generator &&&&&&&&&&&&&&&&&&&&&&')
                        print('**************************** item-content **************************', item.get('content'))
                        
                        _insight = parse_agent_content_json(item.get('content'))
                        python_code = _insight.get('python_code', None)
                        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ python_code ################################################', python_code)
                        python_code_explanation = _insight.get('python_code_explanation', None)

                        sql_query = _insight.get('sql_query', None)
                        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ sql_query ################################################', sql_query)

                        sql_answer = _insight.get('sql_answer', None)
                        print('$$$$$$$$$$$$$$$$$$$ $$$$$$$$$$$$$$$$$$$$$$$$$$$$ sql_answer ################################################', sql_answer)

                    if item['name'] == 'llm_answer_maker':
                        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ llm_answer ################################################', item['content'])
                        llm_answer = item['content']

                    if item['name'] == "retriever":
                        data_points = item['content']

                    sql_answer = sql_answer or ""
                    llm_answer = llm_answer or ""

                    if not sql_answer and item.get('name') == 'Insight_Generator':
                        sql_answer = str(item.get('content') or "")

                    final_answer = {
                        "sql_answer": sql_answer,
                        "llm_answer": llm_answer
                    }
                    

                    
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ final_answer ################################################', final_answer)               
        
        total_tokens = total_tokens_from_autogen_cost(chat_history)
        # print('########################### total_tokens ##############################', total_tokens)
        

        thoughts_list = []
        for msg in groupchat.messages:
            role = msg.get("role")
            name = msg.get("name")
            content = msg.get("content")
            thoughts_list.append(f'<div style="border: 1px solid #ccc; padding: 20px; border-radius: 5px; width: fit-content;">'
                    f'<h2>{name}</h2><br /><h4>Role: {role}</h4><br />{content}</div>')

        thoughts = "\n <br/> <br />".join(thoughts_list)

        # print('data_points', data_points)
        # print('thoughts', thoughts)
        # print('chat_history.summary', chat_history.summary)
        # print('################### chat_history.summary ###########################', chat_history)
        
        formated_answer = formating_final_answer(final_answer)
        
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ formated_answer ################################################', formated_answer)
        
        formated_final_answer = json.loads(formated_answer.replace("```json", "").replace("```", "").strip())
                    
        print('$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ formated_final_answer ################################################', formated_final_answer)
        
        
        #response = {"data_points": json.loads(data_points)  , "answer": formated_final_answer, "thoughts": thoughts, "sql_query": sql_query, "token_usage":total_tokens}

        try:
            if isinstance(data_points, str) and data_points.strip():
                parsed_data_points = json.loads(data_points)
            elif isinstance(data_points, dict):
                parsed_data_points = data_points
            else:
                parsed_data_points = {}
        except Exception as e:
            print("Warning: unable to parse data_points:", e)
            parsed_data_points = {}

        response = {
            "data_points": parsed_data_points,
            "answer": formated_final_answer,
            "thoughts": thoughts,
            "sql_query": sql_query,
            "token_usage": total_tokens
        }
        if python_code:
            response["python_code"] = python_code
            generated_plot = plot_to_base64(python_code)
            if generated_plot:
                response["plot_base64"] = "data:image/png;base64," + generated_plot
            else:
                # Keep response successful even if generated python plot code fails.
                print("Plot generation failed; continuing without plot_base64.")
        if sql_code_explanation:
            response["sql_explanation"] = sql_explanation
            if python_code_explanation:
                response["python_code_explanation"] = python_code_explanation
    del chat_history
    del groupchat
    del manager
    del user_proxy
    cache_path = os.path.join(os.getcwd(), '.cache')

    # Check if it's a directory before deleting
    if os.path.isdir(cache_path):
        shutil.rmtree(cache_path)
        print(f"Deleted directory: {cache_path}")
    response["agent_latencies"] = {k: round(v, 3) for k, v in agent_latency.items()}
    response["orchestration_total_latency_sec"] = round(end - start, 3)
    return response