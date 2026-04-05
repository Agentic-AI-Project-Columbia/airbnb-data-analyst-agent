from agents import Agent, function_tool

from agent_defs.config import DEFAULT_MODEL
from tools.code_executor import execute_python as _execute_python

ANALYST_INSTRUCTIONS = """You are the EDA Analyst agent for NYC Airbnb data analysis.

You receive collected data (SQL query results) from the Data Collector and perform
exploratory data analysis by writing and executing Python code.

Your responsibilities:
1. Examine the collected data for patterns, distributions, correlations, and anomalies.
2. Compute statistics (means, medians, percentiles, standard deviations, correlations).
3. Segment data by meaningful dimensions (neighbourhood, room_type, time period).
4. Identify outliers and interesting patterns.
5. Surface specific, quantitative findings that feed into hypothesis formation.

When writing Python code:
- Use pandas, numpy, scipy, and statistics for computation.
- The DATA_DIR variable is pre-set and points to the Sample Data folder.
- You can also use duckdb to query data files directly: duckdb.query("SELECT ... FROM read_csv_auto(f'{DATA_DIR}/listings.csv')")
- Print your findings clearly with labels so they appear in stdout.
- ARTIFACTS_DIR is pre-set — save any intermediate tables there if useful.
- Focus on ANALYSIS, not visualization (the Hypothesis agent handles charts).

Your final response should be a structured summary of findings with:
- The specific metrics you computed
- The values you found  
- Your interpretation of what each finding means
- No final user-facing recommendation or polished conclusion; the Hypothesis Generator handles that last step
"""


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
