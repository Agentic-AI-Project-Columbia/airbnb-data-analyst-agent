from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.code_executor import execute_python as _execute_python
from tools.sql_runner import run_sql, get_schema_description
from prompts import load_prompt

PRESENTER_INSTRUCTIONS = load_prompt("presenter").replace(
    "{SCHEMA_INFO}", get_schema_description()
)


@function_tool
def create_visualization(code: str) -> str:
    """Execute Python code to generate presentation-quality data visualizations.
    Use matplotlib/seaborn to create polished charts. Save figures to the local
    filesystem directory stored in ARTIFACTS_DIR as PNG; do not save directly to
    /artifacts/... URLs. DATA_DIR and ARTIFACTS_DIR are available as both Python
    variables and os.environ values.
    Returns stdout, stderr, exit_code, and artifact paths for generated charts.
    """
    return _execute_python(code, require_artifacts=True)


@function_tool
def query_database(sql: str) -> str:
    """Execute a SQL query against the NYC Airbnb DuckDB database.
    Returns columns, row_count, and data as JSON."""
    return run_sql(sql)


@function_tool
def run_analysis_code(code: str) -> str:
    """Execute Python code for data analysis. DATA_DIR and ARTIFACTS_DIR are available
    as both Python variables and os.environ values. Returns stdout, stderr,
    exit_code, and any artifacts."""
    return _execute_python(code)


# Sub-agents that the Presenter can hand off to for more data
_presenter_collector = Agent(
    name="Data Collector",
    instructions=(
        get_schema_description() + "\n\n"
        "You are assisting the Presenter agent. Run the SQL query needed to get "
        "the requested data, return the results, then hand off back to the Presenter."
    ),
    tools=[query_database],
    model=DEFAULT_MODEL,
)

_presenter_analyst = Agent(
    name="EDA Analyst",
    instructions=(
        "You are assisting the Presenter agent. Run the requested Python analysis, "
        "return the results, then hand off back to the Presenter.\n"
        "DATA_DIR and ARTIFACTS_DIR are available as both Python variables and "
        "environment variables in your code."
    ),
    tools=[run_analysis_code],
    model=DEFAULT_MODEL,
)

presenter_agent = Agent(
    name="Presenter",
    instructions=PRESENTER_INSTRUCTIONS,
    tools=[create_visualization],
    handoffs=[_presenter_collector, _presenter_analyst],
    model=DEFAULT_MODEL,
)

# Set handoffs back to Presenter (must be done after presenter_agent exists)
_presenter_collector.handoffs = [presenter_agent]
_presenter_analyst.handoffs = [presenter_agent]
