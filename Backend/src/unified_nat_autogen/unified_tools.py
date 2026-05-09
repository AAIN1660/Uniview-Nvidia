import json
import os
import urllib
from collections.abc import AsyncIterator


from sqlalchemy import create_engine
from pydantic import Field
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig

# NOTE:
# The primary orchestration now delegates to utility.inference.start_agenting_process
# via unified_autogen_team.py. These NAT tools are kept for plugin compatibility and
# optional direct tool invocation, but they are not the source-of-truth orchestration.

def _clean_env(value: str | None, default: str | None = None) -> str | None:
    value = value if value is not None else default
    if value is None:
        return None
    value = str(value).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    return value


class ExecuteSQLQueryConfig(
    FunctionBaseConfig,
    name="execute_sql_query"
):
    description: str = Field(default="Execute a SQL Server query")


@register_function(config_type=ExecuteSQLQueryConfig)
async def execute_sql_query(
    config: ExecuteSQLQueryConfig,
    builder
) -> AsyncIterator[FunctionInfo]:

    async def _execute_sql_query(query: str) -> str:
        import pandas as pd
        host = _clean_env(os.getenv("SQL_HOST"))
        database = _clean_env(os.getenv("SQL_DATABASE"))
        username = _clean_env(os.getenv("SQL_USERNAME"))
        password = _clean_env(os.getenv("SQL_PASSWORD"))
        driver = _clean_env(os.getenv("SQL_DRIVER"), "ODBC Driver 18 for SQL Server")

        if not all([host, database, username, password]):
            return "SQL execution error: Missing SQL connection environment variables."

        connection_string = (
            "mssql+pyodbc:///?odbc_connect="
            + urllib.parse.quote_plus(
                f"DRIVER={driver};"
                f"SERVER={host};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                "Encrypt=yes;"
                "TrustServerCertificate=no;"
                "Connection Timeout=30;"
            )
        )

        try:
            engine = create_engine(connection_string)
            df = pd.read_sql(query, engine)
            return df.to_json(orient="records")
        except Exception as e:
            return f"SQL execution error: {str(e)}"

    yield FunctionInfo.from_fn(
        _execute_sql_query,
        description="Execute SQL Server query and return JSON rows."
    )


class RetrieveContextConfig(
    FunctionBaseConfig,
    name="retrieve_context"
):
    description: str = Field(default="Retrieve semantic context")


@register_function(config_type=RetrieveContextConfig)
async def retrieve_context(
    config: RetrieveContextConfig,
    builder
) -> AsyncIterator[FunctionInfo]:

    async def _retrieve_context(question: str, index_type: str = "vector") -> str:
        """
        Initial implementation:
        Keep this simple first.
        Later wire this to your existing Azure Search / Zilliz / GraphRAG logic.
        """
        return json.dumps({
            "question": question,
            "index_type": index_type,
            "context": [],
            "message": "Semantic retrieval NAT hook is active. Connect this to existing retrieval logic."
        })

    yield FunctionInfo.from_fn(
        _retrieve_context,
        description="Retrieve vector/graph/hybrid context for the question."
    )