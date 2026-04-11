from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.code_executor import execute_python as _execute_python
from tools.sql_runner import get_schema_description
from prompts import load_prompt

HYPOTHESIZER_INSTRUCTIONS = load_prompt("hypothesizer").replace(
    "{SCHEMA_INFO}", get_schema_description()
)


@function_tool
def create_visualization(code: str) -> str:
    """Execute Python code to generate data visualizations.
    Use matplotlib/seaborn to create charts. Save figures to the local filesystem
    directory stored in ARTIFACTS_DIR as PNG; do not save directly to /artifacts/...
    URLs. DATA_DIR and ARTIFACTS_DIR are available as both Python variables and
    os.environ values.
    Returns stdout, stderr, exit_code, and artifact paths for generated charts.
    """
    return _execute_python(code, require_artifacts=True)


hypothesizer_agent = Agent(
    name="Hypothesis Generator",
    instructions=HYPOTHESIZER_INSTRUCTIONS,
    tools=[create_visualization],
    model=DEFAULT_MODEL,
)
