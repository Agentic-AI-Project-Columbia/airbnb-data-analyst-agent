import os
import sys
import json
import time
import asyncio

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

sys.path.insert(0, os.path.dirname(__file__))

from openai import AsyncOpenAI

from agents import (
    ItemHelpers,
    MultiProvider,
    RunConfig,
    set_default_openai_client,
    set_tracing_disabled,
)

openrouter_key = os.environ.get("OPENROUTER_API_KEY")
openai_key = os.environ.get("OPENAI_API_KEY")

if openrouter_key:
    openrouter_client = AsyncOpenAI(
        api_key=openrouter_key,
        base_url="https://openrouter.ai/api/v1",
    )
    set_default_openai_client(openrouter_client, use_for_tracing=False)
    OPENROUTER_RUN_CONFIG = RunConfig(
        model_provider=MultiProvider(
            openai_client=openrouter_client,
            openai_prefix_mode="model_id",
            unknown_prefix_mode="model_id",
        )
    )
    set_tracing_disabled(True)
else:
    OPENROUTER_RUN_CONFIG = None

if not openrouter_key and not openai_key:
    print("WARNING: No OPENROUTER_API_KEY or OPENAI_API_KEY found in environment.")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from agents import Runner
from agent_defs.orchestrator import orchestrator_agent

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

app = FastAPI(title="Airbnb Multi-Agent Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")


@app.get("/health")
async def health():
    return {"status": "ok"}


def _collect_artifacts() -> list[str]:
    artifacts = []
    if os.path.exists(ARTIFACTS_DIR):
        for run_dir in os.listdir(ARTIFACTS_DIR):
            run_path = os.path.join(ARTIFACTS_DIR, run_dir)
            if os.path.isdir(run_path):
                for f in os.listdir(run_path):
                    artifacts.append(f"/artifacts/{run_dir}/{f}")
    return artifacts


def _collect_new_artifacts(existing_artifacts: set[str]) -> list[str]:
    current_artifacts = set(_collect_artifacts())
    return sorted(current_artifacts - existing_artifacts)


def _build_runner_input(question: str, history: list[dict] | None):
    if not history:
        return question

    transcript_lines = []
    previous_user_questions = []
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
            speaker = "User" if role == "user" else "Assistant"
            transcript_lines.append(f"{speaker}: {content.strip()}")
            if role == "user":
                previous_user_questions.append(content.strip())

    lowered_question = question.lower()
    is_visual_follow_up = any(
        keyword in lowered_question
        for keyword in ("visual", "chart", "plot", "graph")
    )
    if is_visual_follow_up and previous_user_questions:
        original_question = previous_user_questions[-1]
        return (
            f"{original_question}\n\n"
            "Please continue the same analysis and include a visualization in the "
            "final answer."
        )

    transcript = "\n".join(transcript_lines)
    return (
        "You are continuing an existing conversation about NYC Airbnb analysis.\n"
        "Use the prior conversation to resolve references like 'same', 'that', "
        "'those', or 'previous result'. If the referent is present in the history, "
        "do not ask the user to restate it.\n\n"
        f"Conversation so far:\n{transcript}\n\n"
        f"Latest user request:\n{question}"
    )


def _safe_truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... ({len(text) - limit} chars truncated)"


def _has_visible_trace_steps(trace: list[dict]) -> bool:
    return any(
        step.get("type") != "agent_start" or step.get("agent") != "Orchestrator"
        for step in trace
    )


def _finalize_trace(trace: list[dict], current_agent: str, final_output: str | None) -> list[dict]:
    if not trace:
        trace.append({
            "type": "agent_start",
            "agent": "Orchestrator",
            "ts": time.time(),
        })

    if not _has_visible_trace_steps(trace):
        trace.append({
            "type": "message",
            "agent": current_agent,
            "content": "The orchestrator completed the analysis and prepared the final answer.",
            "ts": time.time(),
        })

    if final_output and not any(step.get("type") == "message" for step in trace):
        trace.append({
            "type": "message",
            "agent": current_agent,
            "content": _safe_truncate(str(final_output), 500),
            "ts": time.time(),
        })

    return trace


@app.post("/api/analyze")
async def analyze(payload: dict):
    """HTTP endpoint: accepts {"question": "..."} and returns the full analysis with agent trace."""
    question = payload.get("question", "")
    history = payload.get("history")
    if not question:
        return JSONResponse(status_code=400, content={"error": "No question provided"})

    try:
        existing_artifacts = set(_collect_artifacts())
        result = Runner.run_streamed(
            orchestrator_agent,
            input=_build_runner_input(question, history),
            run_config=OPENROUTER_RUN_CONFIG,
        )
        trace: list[dict] = []
        current_agent = "Orchestrator"

        async for event in result.stream_events():
            if event.type == "agent_updated_stream_event":
                current_agent = event.new_agent.name
                trace.append({
                    "type": "agent_start",
                    "agent": current_agent,
                    "ts": time.time(),
                })

            elif event.type == "run_item_stream_event":
                if event.item.type == "handoff_output_item":
                    source = event.item.source_agent.name
                    target = event.item.target_agent.name
                    trace.append({
                        "type": "handoff",
                        "source": source,
                        "target": target,
                        "ts": time.time(),
                    })

                elif event.item.type == "tool_call_item":
                    raw = event.item.raw_item
                    tool_name = getattr(raw, "name", None) or "unknown"
                    tool_args = getattr(raw, "arguments", None) or ""
                    trace.append({
                        "type": "tool_call",
                        "agent": current_agent,
                        "tool": tool_name,
                        "input": _safe_truncate(tool_args, 3000),
                        "ts": time.time(),
                    })

                elif event.item.type == "tool_call_output_item":
                    output = str(event.item.output) if event.item.output else ""
                    trace.append({
                        "type": "tool_output",
                        "agent": current_agent,
                        "output": _safe_truncate(output),
                        "ts": time.time(),
                    })

                elif event.item.type == "message_output_item":
                    text = ItemHelpers.text_message_output(event.item)
                    if text.strip():
                        trace.append({
                            "type": "message",
                            "agent": current_agent,
                            "content": _safe_truncate(text, 500),
                            "ts": time.time(),
                        })

        return {
            "answer": result.final_output,
            "artifacts": _collect_new_artifacts(existing_artifacts),
            "trace": _finalize_trace(trace, current_agent, result.final_output),
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    """WebSocket endpoint for streaming agent progress with live trace events."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            question = message.get("question", "")
            history = message.get("history")

            if not question:
                await websocket.send_json({"type": "error", "content": "No question"})
                continue

            await websocket.send_json({
                "type": "status",
                "content": "Starting analysis pipeline...",
                "agent": "Orchestrator",
            })

            try:
                existing_artifacts = set(_collect_artifacts())
                result = Runner.run_streamed(
                    orchestrator_agent,
                    input=_build_runner_input(question, history),
                    run_config=OPENROUTER_RUN_CONFIG,
                )
                current_agent = "Orchestrator"

                async for event in result.stream_events():
                    if event.type == "agent_updated_stream_event":
                        current_agent = event.new_agent.name
                        await websocket.send_json({
                            "type": "trace",
                            "step": {"type": "agent_start", "agent": current_agent, "ts": time.time()},
                        })

                    elif event.type == "run_item_stream_event":
                        if event.item.type == "handoff_output_item":
                            await websocket.send_json({
                                "type": "trace",
                                "step": {
                                    "type": "handoff",
                                    "source": event.item.source_agent.name,
                                    "target": event.item.target_agent.name,
                                    "ts": time.time(),
                                },
                            })
                        elif event.item.type == "tool_call_item":
                            raw = event.item.raw_item
                            await websocket.send_json({
                                "type": "trace",
                                "step": {
                                    "type": "tool_call",
                                    "agent": current_agent,
                                    "tool": getattr(raw, "name", "unknown"),
                                    "input": _safe_truncate(getattr(raw, "arguments", "") or "", 3000),
                                    "ts": time.time(),
                                },
                            })

                await websocket.send_json({
                    "type": "result",
                    "content": result.final_output,
                    "artifacts": _collect_new_artifacts(existing_artifacts),
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Analysis failed: {str(e)}",
                })

    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
