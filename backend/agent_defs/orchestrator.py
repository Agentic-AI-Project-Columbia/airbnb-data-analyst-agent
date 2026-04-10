from agents import Agent

from agent_defs.config import DEFAULT_MODEL
from agent_defs.collector import collector_agent
from agent_defs.analyst import analyst_agent
from agent_defs.hypothesizer import hypothesizer_agent
from agent_defs.presenter import presenter_agent
from prompts import load_prompt

ORCHESTRATOR_INSTRUCTIONS = load_prompt("orchestrator")

orchestrator_agent = Agent(
    name="Orchestrator",
    instructions=ORCHESTRATOR_INSTRUCTIONS,
    handoffs=[collector_agent, analyst_agent, hypothesizer_agent, presenter_agent],
    model=DEFAULT_MODEL,
)
