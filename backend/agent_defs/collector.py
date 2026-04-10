from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.sql_runner import run_sql, get_schema_description
from prompts import load_prompt

COLLECTOR_INSTRUCTIONS = load_prompt("collector").format(
    SCHEMA_INFO=get_schema_description()
)


@function_tool
def query_database(sql: str) -> str:
    """Execute a SQL query against the NYC Airbnb DuckDB database.
    The database contains tables: listings, reviews, and neighbourhoods.
    Only SELECT queries are allowed. Results are returned as JSON with columns, row_count, and data.
    """
    return run_sql(sql)


collector_agent = Agent(
    name="Data Collector",
    instructions=COLLECTOR_INSTRUCTIONS,
    tools=[query_database],
    model=DEFAULT_MODEL,
)
