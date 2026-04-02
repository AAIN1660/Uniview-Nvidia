#import streamlit as st
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


load_dotenv("unified.env")

category_name = (os.getenv("UNIFIED_CATEGORY_NAME") or "retail").strip()
index_name = (os.getenv("UNIFIED_INDEX_NAME") or "ecommerce_data").strip()
search_method = (os.getenv("UNIFIED_SEARCH_METHOD") or "vector").strip()
# category_name = "hr"
# index_name = "eryl_eval"

def generate_answer(user_question):
    answer= 'answer'
    return answer
### core code ###


# Azure Cognitive Search configuration
AZURE_SEARCH_SERVICE_ENDPOINT = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
AZURE_SEARCH_ADMIN_KEY = os.getenv("AZURE_SEARCH_ADMIN_KEY")
AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL") or "text-embedding-3-small"
AZURE_OPENAI_EMBEDDING_MODEL_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL_NAME") or AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL
GPT4_LLM_MODEL_DEPLOYMENT_NAME = os.getenv("GPT4_LLM_MODEL_DEPLOYMENT_NAME") or os.getenv("GPT3_LLM_MODEL_DEPLOYMENT_NAME") or "gpt-4o"
OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE") or "azure"
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-01"
AZURE_OPENAI_API_BASE = os.getenv("AZURE_OPENAI_API_BASE")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
azure_search_credential = AzureKeyCredential(AZURE_SEARCH_ADMIN_KEY)

print(GPT4_LLM_MODEL_DEPLOYMENT_NAME)

# LLM configuration
llm_config = {
    "config_list":[
    {
        "model": GPT4_LLM_MODEL_DEPLOYMENT_NAME,
        "api_type": "azure",
        "base_url": AZURE_OPENAI_API_BASE,
        "api_key":AZURE_OPENAI_API_KEY,
        "api_version":AZURE_OPENAI_API_VERSION,
        }
],
    # "seed": 47,
    "temperature": 0.1,
    # "max_tokens": -1,
    # "request_timeout": 6000
}

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_API_BASE
)

model = AZURE_OPENAI_EMBEDDING_DEPLOYED_MODEL

def generate_embeddings(text, client, embedding_model_deployment_name):
    embeddings = client.embeddings.create(input=[text], model=embedding_model_deployment_name).data[0].embedding
    return embeddings

search_client = SearchClient(endpoint=AZURE_SEARCH_SERVICE_ENDPOINT,index_name=index_name,
                             credential=azure_search_credential
                             )
# File paths and configuration
INPUT_DIR = os.getenv("GRAPHRAG_INPUT_DIR") or "Backend/artifacts"
LANCEDB_URI = f"{INPUT_DIR}/lancedb"
COMMUNITY_REPORT_TABLE = "create_final_community_reports"
ENTITY_TABLE = "create_final_nodes"
ENTITY_EMBEDDING_TABLE = "create_final_entities"
RELATIONSHIP_TABLE = "create_final_relationships"
TEXT_UNIT_TABLE = "create_final_text_units"
COMMUNITY_LEVEL = 3

# Load data
entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
entity_embedding_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_EMBEDDING_TABLE}.parquet")
relationship_df = pd.read_parquet(f"{INPUT_DIR}/{RELATIONSHIP_TABLE}.parquet")
relationships = read_indexer_relationships(relationship_df)
entities = read_indexer_entities(entity_df, entity_embedding_df, COMMUNITY_LEVEL)

description_embedding_store = LanceDBVectorStore(collection_name="entity_description_embeddings")
description_embedding_store.connect(db_uri=LANCEDB_URI)
entity_description_embeddings = store_entity_semantic_embeddings(entities=entities, vectorstore=description_embedding_store)

report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
reports = read_indexer_reports(report_df, entity_df, COMMUNITY_LEVEL)
text_unit_df = pd.read_parquet(f"{INPUT_DIR}/{TEXT_UNIT_TABLE}.parquet")
text_units = read_indexer_text_units(text_unit_df)

# GraphRAG LLM and embedding configurations
api_key = os.getenv("GRAPH_RAG_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
llm_model = os.getenv("GRAPH_RAG_LLM_MODEL") or "gpt-4o"
embedding_model = os.getenv("GRAPH_RAG_EMBEDDING_MODEL_NAME") or "text-embedding-3-small"
api_base = os.getenv("GRAPH_RAG_OPENAI_API_BASE") or os.getenv("AZURE_OPENAI_API_BASE")
api_version = os.getenv("GRAPH_RAG_OPENAI_API_VERSION") or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-01"
api_type = os.getenv("GRAPH_RAG_OPENAI_API_TYPE") or "azure"

llm = ChatOpenAI(
    api_key=api_key,
    api_base=api_base,
    api_version=api_version,
    deployment_name="gpt-4o-08-06",
    model=llm_model,
    api_type=OpenaiApiType.AzureOpenAI,
    max_retries=20,
)

token_encoder = tiktoken.get_encoding("cl100k_base")

text_embedder = OpenAIEmbedding(
    api_key=api_key,
    api_base=api_base,
    api_version=api_version,
    api_type=OpenaiApiType.AzureOpenAI,
    model=embedding_model,
    deployment_name=embedding_model,
    max_retries=20,
)
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
local_context_params = {
                "text_unit_prop": 0.5,
                "community_prop": 0.1,
                "conversation_history_max_turns": 5,
                "conversation_history_user_turns_only": True,
                "top_k_mapped_entities": 2,
                "top_k_relationships": 2,
                "include_entity_rank": True,
                "include_relationship_weight": True,
                "include_community_rank": False,
                "return_candidate_context": False,
                "embedding_vectorstore_key": EntityVectorStoreKey.ID,  # set this to EntityVectorStoreKey.TITLE if the vectorstore uses entity title as ids
                "max_tokens": 12_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 5000)
            }

llm_params = {
                "max_tokens": 2_000,  # change this based on the token limit you have on your model (if you are using a model with 8k limit, a good setting could be 1000=1500)
                "temperature": 0.0,
            }
Localsearch_engine = LocalSearch(
                llm=None,
                context_builder=Localcontext_builder,
                token_encoder=token_encoder,
                llm_params=llm_params,
                context_builder_params=local_context_params,
                response_type="single paragraphs",  # free form text describing the response type and format, can be anything, e.g. prioritized list, single paragraph, multiple paragraphs, multiple-page report
            )


# SQLdb credentials Parameters
server = os.getenv("SQL_HOST")
database = os.getenv("SQL_DATABASE")
username = os.getenv("SQL_USERNAME")
password = os.getenv("SQL_PASSWORD")
driver = os.getenv("SQL_DRIVER") or "ODBC Driver 18 for SQL Server"
encoding = os.getenv("SQL_ENCODING") or "ISO-8859-1"

# Step 1: Connection string for Azure SQL Database
connection_string = f'mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}")}'

# Create the SQLAlchemy engine
engine = create_engine(connection_string)

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
all_table_schemas = get_schema_tables(engine, category_name)

print(all_table_schemas)

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
    llm_config=None,
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
    system_message=
"""
1. **Formulate a Direct Answer**:
   - Based on the SQL query,and the output of the Sql_tool provide a clear and concise answer.
   - Ensure that the response accurately reflects the data that would result from the query.
   - Avoid expanding into any semantic interpretation or broader context that isn't covered by the SQL result.

3. **Edge Cases**:
   - If no valid SQL query is provided, explain why the question cannot be answered (e.g., missing fields in the metadata).

   **Strictly follow below output format**
**Example Output**:
{
  "initial_question": "Which city has the largest GDP?",
  "analysis_type": "Dont change the type,keep the same selected by routing agent",
  "sql question" : "sql question",
  "sql_query": "SELECT city_name, GDP FROM city_stats ORDER BY GDP DESC LIMIT 1;",
  "sql_answer": "The city with the largest GDP is Tokyo, with a GDP of approximately 1.5 trillion USD."
}""",
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
- "semantic_question": The refined question focused on the SQL answer’s primary insight.if the analysis type is both independent then both part of question indepependent of each other so review carefully and if they have no connection pass second independent part.

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
   - Only pass the updated question.

**Output Format**:
{
  "initial_question": "initial_question",
  "analysis_type": "analysis_type",
  "sql_query": "sql_query",
  "sql_answer": "sql_answer",
  "updated_question": "updated_question",
  
}

Example:
If you receive an initial question "What factors contribute to economic growth?", and `updated_question` is "What steps has the United States taken to improve its GDP?", output should be:
{
  "initial_question": "What factors contribute to economic growth?",
  "analysis_type": "SQL",
  "sql_query": "SELECT * FROM economic_growth_factors;",
  "sql_answer": "Key factors include GDP growth, innovation, and trade policy.",
  "updated_question": "What steps has the United States taken to improve its GDP?"
}

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
5. strictly stick to the below mention output format.

**Output Format**:

-if analysis type if symentic based:
{
  "initial_question": "initial_question",
  "analysis_type": "analysis_type",
  "LLM_answer" : "answer generated by the llm answer maker"
  "Complete_answer": "LLM_answer"
}

- if analysis type is both-dependent:

{
  "initial_question": "initial_question",
  "analysis_type": "analysis_type",
  "sql_answer": "sql_answer",
  "updated_question": "updated_question",
  "LLM_answer" : "answer generated by the llm answer maker"
  "Complete_answer": "LLM_answer"

}

- if analysis type is both independent:
{
  "initial_question": "initial_question",
  "analysis_type": "analysis_type",
  "sql_answer": "sql_answer",
  "updated_question": "updated_question",
  "LLM_answer" : "answer generated by the llm answer maker"
  "Complete_answer": "final answer after carefully reviewing the sql_answer and LLM_answer and it must include the sql_answer part if it is not null and the llm_answer"

}
    """,
    llm_config=llm_config,
    max_consecutive_auto_reply=4,
    description="This agent will frame the detailed answer.",
    is_termination_msg=lambda msg: "Happy with the answer" in msg["content"]
)

critic_agent = AssistantAgent(
    name="critic_agent",
    system_message="""You are the critic_agent. Your role is to validate the LLM_answer based on the updated_question and the context.

    **Inputs**:

    1. initial_question
    2. sql_answer
    3. updated_question
    3. LLM_answer

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

    **Output Format**
    - If the answer requires more context to complete:
    
    ```json
    {
        "question": "Original Question",
        "llm_answer": "llm_answer given by the llm_answer_maker.",
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
    ```

    - If the answer is complete and validated, and no further context is required:
    
    ```json
    {
        "question": "Original Question",
        "llm_answer": "llm_answer given by the llm_answer_maker.",
        "Complete_answer": "final answer after carefully reviewing the sql_answer and LLM_answer this should be a combine form of sql answer and LLM answer"
        "scores": {
            "Helpfulness": X,
            "Relevance": Y,
            "Level of Detail": Z,
            "Groundedness": A,
            "Completeness": B,
            "Faithfulness": E
        },
        "feedback_query": "None",
        "feedback_detail": "None"
    }
    "Happy with the answer"
    ```

    - Add "Happy with the answer" after the JSON output only if all scores are satisfactory and 'feedback_query' is 'None'.
    
    """,
    llm_config=llm_config,
    max_consecutive_auto_reply=4,
    description="This agent will validate it using predefined parameters, and form feedback queries if needed.",
    is_termination_msg=lambda msg: "Happy with the answer" in msg["content"]
)


import asyncio
@retriever.register_for_execution()
@Selector_agent.register_for_llm(description="Retrieve relevant context from the vector database or graph database or from both by executing the extract_context function.")
async def extract_context(question: str = None, selector: str = search_method, vector_weight: float = 0.5, graph_weight: float = 0.5) -> dict:
    if not question:
        print("No question provided")
        return {}

    async def fetch_vector_context():
        vector_query = VectorizedQuery(vector=generate_embeddings(question, client, model), k_nearest_neighbors=3, fields="embedding")
        results = search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            select=['documentId', 'content'],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name='my-semantic-config',
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=3
        )
        return [result["content"] for result in results]

    async def fetch_graph_context():
        return Localcontext_builder.build_context(question, top_k_mapped_entities=2, top_k_relationships=2)

    # Fetch contexts based on selector
    if selector == "vector":
        vector_context = await fetch_vector_context()
        print(vector_context)
        return {"vector_context": vector_context}

    elif selector == "graph":
        graph_context = await fetch_graph_context()
        return {"graph_context": graph_context}

    elif selector == "hybrid":
        vector_context, graph_context = await asyncio.gather(fetch_vector_context(), fetch_graph_context())
        combined_context = {
            "combined_context": f"VectorDB context: [{vector_context}, with weight: {vector_weight}], "
                                f"GraphDB context: [{graph_context}, with weight: {graph_weight}]",
            "question": question
        }
        return combined_context

    else:
        print("Invalid selector provided")
        return {}


@Sql_tool.register_for_execution()
@Sql_Executor.register_for_llm(description="You will execute the function and get the result")
def execute_query(query: str = None):
    "takes query as input and return query result in a dataframe object"
    try:
        # Execute the query and fetch the result into a DataFrame
        df = pd.read_sql(query, engine)
        result_json = df.to_json(orient="records")
        return result_json
    except Exception as e:
        # print("An error occurred while executing the query:", e)
        return f"An error occurred while execusting the query:{e}"


def state_transition(last_speaker, groupchat):
    messages = groupchat.messages
    last_message = messages[-1]["content"]
    
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
        if "Happy with the result" in last_message:
            return Insight_Generator
        else:
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


def process_chat_history(chat_result):
    chat_result_str = str(chat_result)
    attempt = chat_result_str.count("'name': 'Critic'")
   
    start_word = 'usage_including_cached_inference'
    end_word = 'usage_excluding_cached_inference'
    start_index = chat_result_str.find(start_word) + len(start_word) + 2
    end_index = chat_result_str.find(end_word) - 3
   
    if start_index != -1 and end_index != -1 and start_index < end_index:
        relevant_part = chat_result_str[start_index:end_index]
        items = relevant_part[2:-1].split(", ")
        total_cost = float([item.split(':')[1].strip() for item in items if "'total_cost':" in item][0])
        total_tokens = int([item.split(':')[1].strip()[:-1] for item in items if "'total_tokens':" in item][0])
    else:
        total_cost, total_tokens = 0.0, 0
   
    return attempt, total_cost, total_tokens

#question = "Which category has the highest total sales across all its products? What is the reason for that?"
#question = "Give names of full-time employees who are on sick leave and what are the policy related to it?"
#question = "IDs of male employees who are on paternity leave and what's the policy for this leave?"
#question = "which is the least selling laptop and what are its return policy"
#question = "Which is the least selling laptop and what are its specification?"
#question = "which is the highest selling camera and tell me the specification of Honour magicbook?"
#question = "What is the most expensive product in the dataset and also tell me the initial setup instructions for this product?"
question = "What are the procedures for replacing coin cell batterey in Inspiron 13 7000 laptop?"
#question = "How can we fix the uneven color brightness of display panel in ASUS Vivobook S 15 OLED?"
if question:
    start = time.time()
    templete = f""""question": {question}"""

    chat_history = user_proxy.initiate_chat(
        manager,
        message=templete,
        summary_method="reflection_with_llm"
    )
    end = time.time()

    attempt, cost, token = process_chat_history(chat_history)

    print("cost:", cost)
    print("token count", token)
    print("Total Time Taken : ",end-start)
