import os

_is_openrouter = bool(os.environ.get("OPENROUTER_API_KEY"))

DEFAULT_MODEL = os.environ.get(
    "AGENT_MODEL",
    "openai/gpt-4.1" if _is_openrouter else "gpt-4.1",
)
