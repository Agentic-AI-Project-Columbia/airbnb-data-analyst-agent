from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.code_executor import execute_python as _execute_python
from prompts import load_prompt

PRESENTER_INSTRUCTIONS = load_prompt("presenter")


@function_tool
def create_visualization(code: str) -> str:
    """Execute Python code to generate presentation-quality data visualizations.
    Use matplotlib/seaborn to create polished charts. Save figures to ARTIFACTS_DIR as PNG.
    DATA_DIR points to the CSV data files for direct access if needed.
    Returns stdout, stderr, exit_code, and artifact paths for generated charts.
    """
    return _execute_python(code)


presenter_agent = Agent(
    name="Presenter",
    instructions=PRESENTER_INSTRUCTIONS,
    tools=[create_visualization],
    model=DEFAULT_MODEL,
)
