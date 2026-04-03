import os

_is_openrouter = bool(os.environ.get("OPENROUTER_API_KEY"))

DEFAULT_MODEL = os.environ.get(
    "AGENT_MODEL",
    "anthropic/claude-sonnet-4.6" if _is_openrouter else "gpt-4.1",
)
