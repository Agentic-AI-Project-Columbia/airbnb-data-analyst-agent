from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_DOTENV_PATH = Path(__file__).with_name(".env")
_DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def load_project_dotenv() -> None:
    """Load local development environment variables without overriding real env."""
    load_dotenv(_DOTENV_PATH, override=False)


def get_cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOW_ORIGINS", "").strip()
    if raw == "*":
        return ["*"]
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if origins:
        return origins
    return list(_DEFAULT_CORS_ORIGINS)
