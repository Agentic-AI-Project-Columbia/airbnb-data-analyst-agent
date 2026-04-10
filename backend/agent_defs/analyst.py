from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.code_executor import execute_python as _execute_python
from prompts import load_prompt

ANALYST_INSTRUCTIONS = load_prompt("analyst")


@function_tool
def run_analysis_code(code: str) -> str:
    """Execute Python code for exploratory data analysis.
    The code has access to pandas, numpy, scipy, duckdb, and other data libraries.
    DATA_DIR points to the CSV data files. ARTIFACTS_DIR is available for saving outputs.
    Returns stdout, stderr, exit_code, and any saved artifact paths.
    """
    return _execute_python(code)


analyst_agent = Agent(
    name="EDA Analyst",
    instructions=ANALYST_INSTRUCTIONS,
    tools=[run_analysis_code],
    model=DEFAULT_MODEL,
)
