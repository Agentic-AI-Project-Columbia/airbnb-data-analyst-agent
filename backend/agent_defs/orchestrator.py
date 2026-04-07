from agents import Agent

from agent_defs.config import DEFAULT_MODEL
from agent_defs.collector import collector_agent
from agent_defs.analyst import analyst_agent
from agent_defs.hypothesizer import hypothesizer_agent
from agent_defs.presenter import presenter_agent

ORCHESTRATOR_INSTRUCTIONS = """You are the Orchestrator for an NYC Airbnb data analysis system.

When a user asks a data question, you coordinate four specialist agents:

1. **Data Collector** — Retrieves raw data by querying the Airbnb database (calendar,
   listings, reviews, neighbourhoods). Hand off to this agent first.

2. **EDA Analyst** — Takes collected data and performs exploratory analysis using Python
   code execution (statistics, distributions, correlations). Hand off after collection.

3. **Hypothesis Generator** — Synthesizes findings into a hypothesis with evidence and
   generates supporting visualizations. Hand off third.

4. **Presenter** — Takes all findings and crafts a polished, insight-driven final answer
   for the user. Hand off last.

Workflow:
- When you receive a user question, hand off to the Data Collector with the question.
- When the Collector returns data, hand off to the EDA Analyst with the collected data.
- When the Analyst returns findings, hand off to the Hypothesis Generator with the findings.
- When the Hypothesis Generator returns, hand off to the Presenter with the full context.
- The Presenter's output is the final answer shown to the user.

Important:
- Pass sufficient context between agents. Include the original question and any prior results.
- If an agent encounters an error, retry once or explain the issue to the user.
- Do not skip steps. All four phases (Collect → Analyze → Hypothesize → Present) must run.
"""

orchestrator_agent = Agent(
    name="Orchestrator",
    instructions=ORCHESTRATOR_INSTRUCTIONS,
    handoffs=[collector_agent, analyst_agent, hypothesizer_agent, presenter_agent],
    model=DEFAULT_MODEL,
)
