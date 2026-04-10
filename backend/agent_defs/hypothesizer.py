from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.code_executor import execute_python as _execute_python
from prompts import load_prompt

HYPOTHESIZER_INSTRUCTIONS = load_prompt("hypothesizer")


@function_tool
def create_visualization(code: str) -> str:
    """Execute Python code to generate data visualizations.
    Use matplotlib/seaborn to create charts. Save figures to ARTIFACTS_DIR as PNG.
    DATA_DIR points to the CSV data files for direct access if needed.
    Returns stdout, stderr, exit_code, and artifact paths for generated charts.
    """
    return _execute_python(code)


hypothesizer_agent = Agent(
    name="Hypothesis Generator",
    instructions=HYPOTHESIZER_INSTRUCTIONS,
    tools=[create_visualization],
    model=DEFAULT_MODEL,
)
