"""Vertex AI provider for the OpenAI Agents SDK.

Uses Google's OpenAI-compatible Chat Completions endpoint so every agent
call goes through Vertex AI without needing the google-cloud-aiplatform SDK.
"""

from __future__ import annotations

import os

import google.auth
import google.auth.transport.requests
from openai import AsyncOpenAI

from agents import (
    ModelProvider,
    OpenAIChatCompletionsModel,
    RunConfig,
    set_default_openai_client,
    set_tracing_disabled,
)


def _build_base_url(project: str, location: str) -> str:
    if location == "global":
        return (
            f"https://aiplatform.googleapis.com"
            f"/v1beta1/projects/{project}/locations/global"
            f"/endpoints/openapi"
        )
    return (
        f"https://{location}-aiplatform.googleapis.com"
        f"/v1beta1/projects/{project}/locations/{location}"
        f"/endpoints/openapi"
    )


class VertexProvider(ModelProvider):
    """Routes all model calls through Vertex AI's Chat Completions endpoint.

    Automatically refreshes the Google auth token when it expires so the
    server can run indefinitely without credential staleness.
    """

    def __init__(self, project: str, location: str) -> None:
        self._creds, _ = google.auth.default()
        self._creds.refresh(google.auth.transport.requests.Request())
        self._client = AsyncOpenAI(
            api_key=self._creds.token,
            base_url=_build_base_url(project, location),
        )

    def get_model(self, model_name: str) -> OpenAIChatCompletionsModel:
        if self._creds.expired:
            self._creds.refresh(google.auth.transport.requests.Request())
            self._client.api_key = self._creds.token
        return OpenAIChatCompletionsModel(
            model=model_name,
            openai_client=self._client,
        )

    @property
    def client(self) -> AsyncOpenAI:
        return self._client

    @property
    def token(self) -> str:
        if self._creds.expired:
            self._creds.refresh(google.auth.transport.requests.Request())
        return self._creds.token


def create_vertex_run_config(
    project: str | None = None,
    location: str | None = None,
) -> tuple[RunConfig, VertexProvider]:
    """Build a RunConfig backed by Vertex AI.

    Returns (run_config, provider) so callers can access the client/token
    if needed for SDK defaults.
    """
    project = project or os.environ.get("GCP_PROJECT_ID")
    location = location or os.environ.get("GCP_LOCATION", "global")

    if not project:
        raise RuntimeError(
            "GCP_PROJECT_ID is required. "
            "Set it in .env or as an environment variable."
        )

    provider = VertexProvider(project, location)

    # SDK internals may check OPENAI_API_KEY even with a custom provider
    os.environ.setdefault("OPENAI_API_KEY", provider.token)
    set_default_openai_client(provider.client, use_for_tracing=False)
    set_tracing_disabled(True)

    run_config = RunConfig(model_provider=provider)
    return run_config, provider
