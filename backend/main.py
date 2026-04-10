import os
import sys
import json
import time
import asyncio
import re
import uuid

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
from agent_defs.collector import collector_agent
from agent_defs.analyst import analyst_agent
from agent_defs.hypothesizer import hypothesizer_agent
from agent_defs.presenter import presenter_agent

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

SHARES_DIR = os.path.join(os.path.dirname(__file__), "shares")
os.makedirs(SHARES_DIR, exist_ok=True)

STAGE_TIMEOUT_SECONDS = 180    # 3 minutes per agent stage
PIPELINE_TIMEOUT_SECONDS = 600  # 10 minutes total

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


@app.get("/api/schema")
async def get_schema():
    """Return schema for all registered DuckDB views."""
    from tools.sql_runner import get_schema_json
    return get_schema_json()


@app.post("/api/share")
async def create_share(payload: dict):
    """Save a conversation snapshot and return a share ID."""
    question = payload.get("question", "")
    answer = payload.get("answer", "")
    if not question or not answer:
        return JSONResponse(status_code=400, content={"error": "question and answer are required"})

    share_id = uuid.uuid4().hex[:10]
    share_data = {
        "id": share_id,
        "question": question,
        "answer": answer,
        "artifacts": payload.get("artifacts", []),
        "trace": payload.get("trace", []),
        "created_at": time.time(),
    }

    share_path = os.path.join(SHARES_DIR, f"{share_id}.json")
    with open(share_path, "w") as f:
        json.dump(share_data, f)

    return {"id": share_id}


@app.get("/api/share/{share_id}")
async def get_share(share_id: str):
    """Retrieve a shared conversation by ID."""
    share_path = os.path.join(SHARES_DIR, f"{share_id}.json")
    if not os.path.exists(share_path):
        return JSONResponse(status_code=404, content={"error": "Share not found"})

    with open(share_path, "r") as f:
        return json.load(f)


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


def _clean_final_answer(text: str) -> str:
    cleaned = text
    # Safety net: strip any remaining fenced Python code blocks
    cleaned = re.sub(
        r"```(?:python|py)[\s\S]*?```",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Remove "see filename:" type references
    cleaned = re.sub(
        r"\s*\(?(?:see (?:filename|file):?|see below for visualization\.?)\s*`?[^`\n)]*`?\)?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Remove standalone bare filenames (but preserve markdown image syntax ![...](path))
    cleaned = re.sub(
        r"(?<!\()`?[\w.-]+\.(?:png|jpg|jpeg|gif|webp|svg)`?(?!\))",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Collapse 3+ consecutive newlines to exactly 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    # Remove lines that contain only whitespace
    cleaned = re.sub(r"\n[ \t]+\n", "\n\n", cleaned)
    return cleaned.strip()


def _inject_inline_images(text: str, artifacts: list[str]) -> str:
    """If the Presenter forgot to embed charts inline, inject them as a safety net."""
    if not artifacts:
        return text

    image_artifacts = [a for a in artifacts if re.search(r'\.(png|jpe?g|gif|webp|svg)$', a, re.IGNORECASE)]
    if not image_artifacts:
        return text

    # Find which artifacts are already referenced via ![...](...) syntax
    referenced = set()
    for match in re.finditer(r'!\[.*?\]\(([^)]+)\)', text):
        referenced.add(match.group(1))

    unreferenced = [a for a in image_artifacts if a not in referenced]
    if not unreferenced:
        return text

    def _artifact_title(path: str) -> str:
        name = path.split('/')[-1].rsplit('.', 1)[0]
        return name.replace('_', ' ').replace('-', ' ').title()

    image_lines = [f"\n\n![{_artifact_title(a)}]({a})" for a in unreferenced]

    # Try to distribute across ## sections
    sections = list(re.finditer(r'^##\s', text, re.MULTILINE))
    if len(sections) >= 2 and len(unreferenced) <= len(sections):
        result = text
        offset = 0
        for i, img_line in enumerate(image_lines):
            if i + 1 < len(sections):
                insert_pos = sections[i + 1].start() - 1 + offset
            else:
                insert_pos = len(result)
            result = result[:insert_pos] + img_line + result[insert_pos:]
            offset += len(img_line)
        return result

    # Fallback: append all at the end
    return text + "\n" + "\n".join(image_lines)


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
            "content": str(final_output),
            "ts": time.time(),
        })

    return trace


async def _record_trace_step(trace: list[dict], step: dict, websocket: WebSocket | None = None) -> None:
    trace.append(step)
    if websocket is not None:
        await websocket.send_json({"type": "trace", "step": step})


async def _run_agent_stage(
    agent,
    stage_input: str,
    trace: list[dict],
    websocket: WebSocket | None = None,
) -> tuple[str, str]:
    current_agent = agent.name
    await _record_trace_step(
        trace,
        {
            "type": "agent_start",
            "agent": current_agent,
            "ts": time.time(),
        },
        websocket,
    )

    result = Runner.run_streamed(
        agent,
        input=stage_input,
        run_config=OPENROUTER_RUN_CONFIG,
    )

    async for event in result.stream_events():
        if event.type == "agent_updated_stream_event":
            current_agent = event.new_agent.name
            await _record_trace_step(
                trace,
                {
                    "type": "agent_start",
                    "agent": current_agent,
                    "ts": time.time(),
                },
                websocket,
            )

        elif event.type == "run_item_stream_event":
            if event.item.type == "handoff_output_item":
                await _record_trace_step(
                    trace,
                    {
                        "type": "handoff",
                        "source": event.item.source_agent.name,
                        "target": event.item.target_agent.name,
                        "ts": time.time(),
                    },
                    websocket,
                )

            elif event.item.type == "tool_call_item":
                raw = event.item.raw_item
                tool_name = getattr(raw, "name", "unknown")
                tool_input = _safe_truncate(getattr(raw, "arguments", "") or "", 3000)
                step = {
                    "type": "tool_call",
                    "agent": current_agent,
                    "tool": tool_name,
                    "input": tool_input,
                    "ts": time.time(),
                }
                # Extract table names from SQL for query_database calls
                if tool_name == "query_database":
                    try:
                        parsed_args = json.loads(tool_input)
                        sql_text = parsed_args.get("sql", parsed_args.get("query", ""))
                    except (json.JSONDecodeError, AttributeError):
                        sql_text = tool_input
                    tables = re.findall(r'(?:FROM|JOIN)\s+(\w+)', sql_text, re.IGNORECASE)
                    step["tables"] = list(dict.fromkeys(tables))  # dedupe preserving order
                await _record_trace_step(trace, step, websocket)

            elif event.item.type == "tool_call_output_item":
                output = str(event.item.output) if event.item.output else ""
                step = {
                    "type": "tool_output",
                    "agent": current_agent,
                    "output": output,
                    "ts": time.time(),
                }
                # Try to extract structured metadata from tool output
                try:
                    parsed_output = json.loads(output)
                    if isinstance(parsed_output, dict):
                        if "row_count" in parsed_output:
                            step["row_count"] = parsed_output["row_count"]
                        if "columns" in parsed_output and isinstance(parsed_output["columns"], list):
                            step["columns"] = parsed_output["columns"]
                        if "data" in parsed_output and isinstance(parsed_output["data"], list):
                            step["preview"] = parsed_output["data"][:3]
                        if "exit_code" in parsed_output:
                            step["exit_code"] = parsed_output["exit_code"]
                        if "artifacts" in parsed_output and isinstance(parsed_output["artifacts"], list):
                            step["artifacts"] = parsed_output["artifacts"]
                except (json.JSONDecodeError, TypeError):
                    pass
                await _record_trace_step(trace, step, websocket)

            elif event.item.type == "message_output_item":
                text = ItemHelpers.text_message_output(event.item)
                if text.strip():
                    await _record_trace_step(
                        trace,
                        {
                            "type": "message",
                            "agent": current_agent,
                            "content": text,
                            "ts": time.time(),
                        },
                        websocket,
                    )

    final_output = result.final_output
    final_text = "" if final_output is None else str(final_output)
    if agent.name in ("Hypothesis Generator", "Presenter"):
        final_text = _clean_final_answer(final_text)
    return current_agent, final_text


def _build_collector_input(resolved_request: str) -> str:
    return (
        "Stage 1 of 4: Data Collection.\n"
        "Collect only the data needed to answer the request.\n"
        "Do not provide the final answer.\n\n"
        f"Resolved user request:\n{resolved_request}"
    )


def _build_analyst_input(resolved_request: str, collector_output: str) -> str:
    return (
        "Stage 2 of 4: Exploratory Data Analysis.\n"
        "Use the collected data below to compute findings, patterns, and caveats.\n"
        "Do not provide the final polished user answer yet.\n\n"
        f"Resolved user request:\n{resolved_request}\n\n"
        f"Collected data:\n{collector_output}"
    )


def _build_hypothesis_input(
    resolved_request: str,
    collector_output: str,
    analyst_output: str,
) -> str:
    return (
        "Stage 3 of 4: Hypothesis and visualization.\n"
        "Use the collected data and analyst findings to form a hypothesis with evidence.\n"
        "Generate visualizations to support key findings.\n"
        "Do not worry about polishing the final output — that happens next.\n\n"
        f"Resolved user request:\n{resolved_request}\n\n"
        f"Collected data:\n{collector_output}\n\n"
        f"Analyst findings:\n{analyst_output}"
    )


def _build_presenter_input(
    resolved_request: str,
    collector_output: str,
    analyst_output: str,
    hypothesis_output: str,
    existing_chart_paths: list[str] | None = None,
) -> str:
    parts = [
        "Stage 4 of 4: Final presentation.\n"
        "Transform the analysis into a polished, insight-driven answer for the user.\n"
        "Do NOT add new analysis — just present what was found in the best possible way.\n\n"
        f"Original user question:\n{resolved_request}\n\n"
        f"Collected data (raw query results):\n{_safe_truncate(collector_output, 4000)}\n\n"
        f"Analyst findings:\n{analyst_output}\n\n"
        f"Hypothesis and evidence:\n{hypothesis_output}"
    ]
    if existing_chart_paths:
        chart_list = "\n".join(f"  - {p}" for p in existing_chart_paths)
        parts.append(
            f"\n\nCharts already generated by previous stages:\n{chart_list}\n"
            "Do NOT recreate these. Only create NEW presentation-quality visualizations "
            "that improve on these or add a different perspective. Aim for 2-3 charts total."
        )
    return "".join(parts)


async def _run_stage_with_timeout(
    agent,
    stage_input: str,
    trace: list[dict],
    websocket: WebSocket | None,
    fallback: str = "",
) -> tuple[str, str]:
    """Run a single agent stage with a timeout. Returns (agent_name, output)."""
    try:
        return await asyncio.wait_for(
            _run_agent_stage(agent, stage_input, trace, websocket),
            timeout=STAGE_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        await _record_trace_step(
            trace,
            {
                "type": "message",
                "agent": agent.name,
                "content": f"Stage timed out after {STAGE_TIMEOUT_SECONDS}s.",
                "ts": time.time(),
            },
            websocket,
        )
        return agent.name, fallback


async def _run_pipeline(
    question: str,
    history: list[dict] | None,
    trace: list[dict],
    websocket: WebSocket | None = None,
) -> str:
    resolved_request = _build_runner_input(question, history)
    initial_artifacts = set(_collect_artifacts())

    await _record_trace_step(
        trace,
        {
            "type": "agent_start",
            "agent": "Orchestrator",
            "ts": time.time(),
        },
        websocket,
    )
    await _record_trace_step(
        trace,
        {
            "type": "message",
            "agent": "Orchestrator",
            "content": "Running a four-stage pipeline: collect data, analyze findings, synthesize hypothesis, then present the final answer.",
            "ts": time.time(),
        },
        websocket,
    )

    # Stage 1: Data Collection
    await _record_trace_step(
        trace,
        {
            "type": "handoff",
            "source": "Orchestrator",
            "target": "Data Collector",
            "ts": time.time(),
        },
        websocket,
    )
    _, collector_output = await _run_stage_with_timeout(
        collector_agent,
        _build_collector_input(resolved_request),
        trace,
        websocket,
    )

    # Stage 2: EDA Analysis
    await _record_trace_step(
        trace,
        {
            "type": "handoff",
            "source": "Data Collector",
            "target": "EDA Analyst",
            "ts": time.time(),
        },
        websocket,
    )
    _, analyst_output = await _run_stage_with_timeout(
        analyst_agent,
        _build_analyst_input(resolved_request, collector_output),
        trace,
        websocket,
    )

    # Stage 3: Hypothesis Generation
    await _record_trace_step(
        trace,
        {
            "type": "handoff",
            "source": "EDA Analyst",
            "target": "Hypothesis Generator",
            "ts": time.time(),
        },
        websocket,
    )
    _, hypothesis_output = await _run_stage_with_timeout(
        hypothesizer_agent,
        _build_hypothesis_input(resolved_request, collector_output, analyst_output),
        trace,
        websocket,
    )

    # Stage 4: Presentation
    pre_presenter_artifacts = set(_collect_artifacts())
    existing_chart_paths = sorted(pre_presenter_artifacts - initial_artifacts)

    await _record_trace_step(
        trace,
        {
            "type": "handoff",
            "source": "Hypothesis Generator",
            "target": "Presenter",
            "ts": time.time(),
        },
        websocket,
    )

    presenter_input = _build_presenter_input(
        resolved_request, collector_output, analyst_output, hypothesis_output,
        existing_chart_paths=existing_chart_paths or None,
    )
    _, final_output = await _run_stage_with_timeout(
        presenter_agent,
        presenter_input,
        trace,
        websocket,
        fallback=_clean_final_answer(hypothesis_output),
    )

    # Validation: if Presenter produced zero charts, retry once with a nudge
    presenter_artifacts = _collect_new_artifacts(pre_presenter_artifacts)
    if not any(re.search(r'\.(png|jpe?g|svg)$', a, re.IGNORECASE) for a in presenter_artifacts):
        nudge_input = (
            presenter_input
            + "\n\nIMPORTANT: Your response MUST include at least one chart. "
            "Call create_visualization now to generate a visualization that supports "
            "your key finding, then embed it with ![title](path)."
        )
        _, final_output = await _run_stage_with_timeout(
            presenter_agent,
            nudge_input,
            trace,
            websocket,
            fallback=final_output,
        )

    # Post-process: inject inline image references for any unreferenced charts
    all_new_artifacts = _collect_new_artifacts(initial_artifacts)
    final_output = _inject_inline_images(final_output, all_new_artifacts)

    await _record_trace_step(
        trace,
        {
            "type": "message",
            "agent": "Orchestrator",
            "content": "The orchestrator completed all four stages and returned the final answer.",
            "ts": time.time(),
        },
        websocket,
    )

    return final_output


@app.post("/api/analyze")
async def analyze(payload: dict):
    """HTTP endpoint: accepts {"question": "..."} and returns the full analysis with agent trace."""
    question = payload.get("question", "")
    history = payload.get("history")
    if not question:
        return JSONResponse(status_code=400, content={"error": "No question provided"})

    try:
        existing_artifacts = set(_collect_artifacts())
        trace: list[dict] = []
        result = await asyncio.wait_for(
            _run_pipeline(question, history, trace),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )

        return {
            "answer": result,
            "artifacts": _collect_new_artifacts(existing_artifacts),
            "trace": _finalize_trace(trace, "Presenter", result),
        }
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"error": f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS}s"})
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
                trace: list[dict] = []
                final_output = await asyncio.wait_for(
                    _run_pipeline(question, history, trace, websocket),
                    timeout=PIPELINE_TIMEOUT_SECONDS,
                )

                await websocket.send_json({
                    "type": "result",
                    "content": final_output,
                    "artifacts": _collect_new_artifacts(existing_artifacts),
                })
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Pipeline timed out after {PIPELINE_TIMEOUT_SECONDS}s. Please try a simpler question.",
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
