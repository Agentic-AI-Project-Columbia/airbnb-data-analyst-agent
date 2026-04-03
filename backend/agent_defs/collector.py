from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.sql_runner import run_sql, get_schema_description

SCHEMA_INFO = get_schema_description()

COLLECTOR_INSTRUCTIONS = f"""You are the Data Collector agent for NYC Airbnb data analysis.

Your job is to translate the user's analytical question into one or more DuckDB SQL
queries and return the raw results. You have access to these tables:

{SCHEMA_INFO}

Key relationships:
- calendar.listing_id joins to listings.id
- reviews.listing_id joins to listings.id  
- listings.neighbourhood_cleansed matches neighbourhoods.neighbourhood

Guidelines:
- Write efficient SQL. Use aggregations, filters, and LIMIT to keep result sets manageable.
- For large scans (calendar has ~13M rows), always use WHERE clauses and aggregations.
- Return meaningful column aliases so results are self-explanatory.
- If the question is ambiguous, make reasonable assumptions and state them.
- You may issue multiple queries if needed to fully answer the question.
- Always include relevant dimensions (neighbourhood, room_type, date ranges) in results.
- Prefer the 'listings' table (detailed, 85 columns) over 'listings_summary' unless simplicity is needed.
"""


@function_tool
def query_database(sql: str) -> str:
    """Execute a SQL query against the NYC Airbnb DuckDB database.
    The database contains tables: calendar, listings, listings_summary, reviews, neighbourhoods.
    Only SELECT queries are allowed. Results are returned as JSON with columns, row_count, and data.
    """
    return run_sql(sql)


collector_agent = Agent(
    name="Data Collector",
    instructions=COLLECTOR_INSTRUCTIONS,
    tools=[query_database],
    model=DEFAULT_MODEL,
)
