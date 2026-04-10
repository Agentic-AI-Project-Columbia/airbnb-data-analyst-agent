from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.code_executor import execute_python as _execute_python
from tools.sql_runner import run_sql, get_schema_description
from prompts import load_prompt

ANALYST_INSTRUCTIONS = load_prompt("analyst").replace(
    "{SCHEMA_INFO}", get_schema_description()
)


@function_tool
def run_analysis_code(code: str) -> str:
    """Execute Python code for exploratory data analysis.
    The code has access to pandas, numpy, scipy, duckdb, and other data libraries.
    DATA_DIR points to the CSV data files. ARTIFACTS_DIR is available for saving outputs.
    Returns stdout, stderr, exit_code, and any saved artifact paths.
    """
    return _execute_python(code)


@function_tool
def query_database(sql: str) -> str:
    """Execute a SQL query against the NYC Airbnb DuckDB database.
    Use this when your analysis reveals data gaps that the initial collected data
    doesn't cover. The database contains tables: listings, reviews, and neighbourhoods.
    Only SELECT queries are allowed. Results are returned as JSON with columns, row_count, and data.
    """
    return run_sql(sql)


analyst_agent = Agent(
    name="EDA Analyst",
    instructions=ANALYST_INSTRUCTIONS,
    tools=[run_analysis_code, query_database],
    model=DEFAULT_MODEL,
)
