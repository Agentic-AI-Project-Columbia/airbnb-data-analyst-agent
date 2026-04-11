from agent_defs.config import DEFAULT_MODEL
from pipeline import create_pipeline_agents

_AGENTS = create_pipeline_agents(DEFAULT_MODEL)

collector_agent = _AGENTS["collector"]
analyst_agent = _AGENTS["analyst"]
hypothesizer_agent = _AGENTS["hypothesizer"]
presenter_agent = _AGENTS["presenter"]
