from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.sql_runner import run_sql, get_schema_description

SCHEMA_INFO = get_schema_description()

COLLECTOR_INSTRUCTIONS = f"""You are the Data Collector agent for NYC Airbnb data analysis.

Your job is to translate the user's analytical question into one or more DuckDB SQL
queries and return the raw results. You have access to these tables:

{SCHEMA_INFO}

Key relationships:
- listings.neighbourhood_cleansed matches neighbourhoods.neighbourhood

Guidelines:
- Write efficient SQL. Use aggregations, filters, and LIMIT to keep result sets manageable.
- This dataset currently includes listings and neighbourhood data only.
- Ignore calendar-based and review-based analysis for now. Do not query missing calendar/review tables or mention missing data unless the user asks.
- Return meaningful column aliases so results are self-explanatory.
- If the question is ambiguous, make reasonable assumptions and state them.
- You may issue multiple queries if needed to fully answer the question.
- Always include relevant dimensions such as neighbourhood and room_type in results.
- Prefer the 'listings' table for analysis.
"""


@function_tool
def query_database(sql: str) -> str:
    """Execute a SQL query against the NYC Airbnb DuckDB database.
    The database contains tables: listings and neighbourhoods.
    Only SELECT queries are allowed. Results are returned as JSON with columns, row_count, and data.
    """
    return run_sql(sql)


collector_agent = Agent(
    name="Data Collector",
    instructions=COLLECTOR_INSTRUCTIONS,
    tools=[query_database],
    model=DEFAULT_MODEL,
)
