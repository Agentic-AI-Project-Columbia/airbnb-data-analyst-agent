import os

DEFAULT_MODEL_ID = "google/gemini-3.5-flash-lite"
DEFAULT_MODEL = os.environ.get("AGENT_MODEL", DEFAULT_MODEL_ID)
