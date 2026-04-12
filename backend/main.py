import os
import sys
import json
import time
import asyncio
import re
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from agents import ItemHelpers
from runtime_config import get_cors_origins, load_project_dotenv

load_project_dotenv()

from agent_defs.config import DEFAULT_MODEL as _DEFAULT_MODEL
from vertex_provider import create_vertex_run_config

# ---------------------------------------------------------------------------
# Provider setup: Vertex AI (Gemini)
# ---------------------------------------------------------------------------
MODEL_RUN_CONFIG, _vertex = create_vertex_run_config()
_gcp_project = os.environ.get("GCP_PROJECT_ID", "")
_gcp_location = os.environ.get("GCP_LOCATION", "us-central1")
print(f"Using Vertex AI  (project={_gcp_project}, location={_gcp_location}, model={_DEFAULT_MODEL})")

from agent_defs import analyst_agent, collector_agent, hypothesizer_agent, presenter_agent
from pipeline import (
    build_analyst_input,
    build_collector_input,
    build_hypothesis_input,
    build_presenter_input,
    clean_final_answer,
    safe_truncate,
)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from agents import Runner

ARTIFACTS_DIR = os.environ.get(
    "ARTIFACTS_DIR",
    os.path.join(os.path.dirname(__file__), "artifacts"),
)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

SHARES_DIR = os.environ.get(
    "SHARES_DIR",
    os.path.join(os.path.dirname(__file__), "shares"),
)
os.makedirs(SHARES_DIR, exist_ok=True)

STAGE_TIMEOUT_SECONDS = 180    # 3 minutes per agent stage
PIPELINE_TIMEOUT_SECONDS = 600  # 10 minutes total
HEARTBEAT_INTERVAL = 30.0      # WebSocket keepalive interval

OUT_OF_SCOPE_LOCATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\blos angeles\b", re.IGNORECASE), "Los Angeles"),
    (re.compile(r"(?<![A-Za-z])LA(?![A-Za-z])"), "Los Angeles"),
    (re.compile(r"\bsan francisco\b", re.IGNORECASE), "San Francisco"),
    (re.compile(r"\bchicago\b", re.IGNORECASE), "Chicago"),
    (re.compile(r"\bmiami\b", re.IGNORECASE), "Miami"),
    (re.compile(r"\bseattle\b", re.IGNORECASE), "Seattle"),
    (re.compile(r"\bboston\b", re.IGNORECASE), "Boston"),
    (re.compile(r"\bwashington dc\b", re.IGNORECASE), "Washington, DC"),
]


async def _heartbeat(websocket: WebSocket) -> None:
    """Send periodic heartbeat messages to keep the WebSocket alive."""
    try:
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            await websocket.send_json({"type": "heartbeat", "ts": time.time()})
    except (asyncio.CancelledError, Exception):
        pass


def _get_scope_error(question: str) -> str | None:
    """Reject obvious non-NYC geographic comparisons before running the pipeline."""
    for pattern, label in OUT_OF_SCOPE_LOCATION_PATTERNS:
        if pattern.search(question):
            return (
                f"This dataset only covers New York City Airbnb listings, so I can't answer "
                f"questions about {label}. Try comparing Brooklyn with another NYC borough "
                f"or neighbourhood instead, such as Manhattan, Queens, the Bronx, or Staten Island."
            )
    return None

app = FastAPI(title="Airbnb Multi-Agent Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,
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


def _extract_artifacts_from_trace(trace: list[dict], start_index: int = 0) -> list[str]:
    """Extract artifact paths from tool_output trace steps (no filesystem scanning)."""
    artifacts: list[str] = []
    seen: set[str] = set()
    for step in trace[start_index:]:
        if step.get("type") != "tool_output":
            continue
        step_artifacts = step.get("artifacts")
        if not isinstance(step_artifacts, list):
            continue
        for art in step_artifacts:
            path = art.get("path") if isinstance(art, dict) else art if isinstance(art, str) else None
            if path and path not in seen:
                seen.add(path)
                artifacts.append(path)
    return artifacts


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


MAX_CHARTS = 4  # Hard cap on total charts in final output


def _is_valid_image(artifact_path: str) -> bool:
    """Check that an artifact file exists and is a non-empty, valid image."""
    # Convert /artifacts/run_id/file.png to filesystem path
    rel = artifact_path.lstrip("/")
    full_path = os.path.join(os.path.dirname(__file__), rel)
    if not os.path.isfile(full_path):
        return False
    size = os.path.getsize(full_path)
    if size < 2000:  # empty/blank charts are typically < 2KB
        return False
    # Check PNG magic bytes
    try:
        with open(full_path, "rb") as f:
            header = f.read(8)
        if full_path.lower().endswith(".png"):
            if header[:4] != b'\x89PNG':
                return False
        # Check for blank/empty images: a mostly-white PNG will be very small
        # relative to its dimensions. Real charts at 150dpi 10x6 are typically > 30KB.
        if size < 5000:
            return False
        return True
    except OSError:
        return False


def _inject_inline_images(text: str, artifacts: list[str]) -> str:
    """If the Presenter forgot to embed charts inline, inject them as a safety net."""
    if not artifacts:
        return text

    image_artifacts = [a for a in artifacts if re.search(r'\.(png|jpe?g|gif|webp|svg)$', a, re.IGNORECASE)]
    # Filter out broken/empty images
    image_artifacts = [a for a in image_artifacts if _is_valid_image(a)]
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


def _agent_made_tool_call(trace: list[dict], agent_name: str, start_index: int = 0) -> bool:
    return any(
        step.get("type") == "tool_call" and step.get("agent") == agent_name
        for step in trace[start_index:]
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
        run_config=MODEL_RUN_CONFIG,
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
                tool_input = safe_truncate(getattr(raw, "arguments", "") or "", 3000)
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
                        if "returned_row_count" in parsed_output:
                            step["returned_row_count"] = parsed_output["returned_row_count"]
                        if "truncated" in parsed_output:
                            step["truncated"] = parsed_output["truncated"]
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
        final_text = clean_final_answer(final_text)
    return current_agent, final_text


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
) -> tuple[str, list[str]]:
    """Run the 4-stage pipeline. Returns (final_output, new_artifact_paths)."""
    resolved_request = _build_runner_input(question, history)
    trace_start = len(trace)

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
        build_collector_input(resolved_request),
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
    analyst_trace_start = len(trace)
    _, analyst_output = await _run_stage_with_timeout(
        analyst_agent,
        build_analyst_input(resolved_request, collector_output),
        trace,
        websocket,
    )

    if not _agent_made_tool_call(trace, "EDA Analyst", analyst_trace_start):
        await _record_trace_step(
            trace,
            {
                "type": "message",
                "agent": "Orchestrator",
                "content": "EDA Analyst returned without using an analysis tool. Retrying with an explicit requirement to compute over the collected data.",
                "ts": time.time(),
            },
            websocket,
        )
        _, analyst_output = await _run_stage_with_timeout(
            analyst_agent,
            build_analyst_input(resolved_request, collector_output)
            + "\n\nIMPORTANT: You must make at least one tool call in this stage using the collected data. "
              "Use run_analysis_code for statistics/computation or query_database for a refined breakdown before responding.",
            trace,
            websocket,
            fallback=analyst_output,
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
        build_hypothesis_input(resolved_request, collector_output, analyst_output),
        trace,
        websocket,
    )

    # Stage 4: Presentation
    existing_chart_paths = _extract_artifacts_from_trace(trace, trace_start)
    presenter_trace_start = len(trace)

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

    presenter_input = build_presenter_input(
        resolved_request, collector_output, analyst_output, hypothesis_output,
        existing_chart_paths=existing_chart_paths or None,
    )
    _, final_output = await _run_stage_with_timeout(
        presenter_agent,
        presenter_input,
        trace,
        websocket,
        fallback=clean_final_answer(hypothesis_output),
    )

    # Validation: if Presenter produced zero charts, retry once with a nudge
    presenter_artifacts = _extract_artifacts_from_trace(trace, presenter_trace_start)
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

    # Post-process: filter out broken/empty images and cap at MAX_CHARTS
    all_new_artifacts = _extract_artifacts_from_trace(trace, trace_start)
    all_new_artifacts = [a for a in all_new_artifacts if _is_valid_image(a)]

    # Deduplicate: keep only uniquely-named charts (skip auto-saved chart_N.png
    # duplicates if a named chart already exists from the same run)
    seen_runs: dict[str, int] = {}  # run_id -> count of named charts
    deduped: list[str] = []
    for a in all_new_artifacts:
        parts = a.strip("/").split("/")
        if len(parts) >= 3:
            run_id = parts[1]
            filename = parts[2]
            is_auto = bool(re.match(r'^chart_\d+\.png$', filename))
            if is_auto and seen_runs.get(run_id, 0) > 0:
                continue  # skip auto-saved duplicate
            if not is_auto:
                seen_runs[run_id] = seen_runs.get(run_id, 0) + 1
        deduped.append(a)
    all_new_artifacts = deduped[:MAX_CHARTS]  # hard cap

    # Strip any inline image references that point to broken/missing files
    # and enforce the cap on already-embedded images too
    valid_set = set(all_new_artifacts)
    def _validate_inline_refs(text: str) -> str:
        kept = []
        def _check(m):
            path = m.group(1)
            if not _is_valid_image(path):
                return ""
            if len(kept) >= MAX_CHARTS:
                return ""
            kept.append(path)
            valid_set.add(path)
            return m.group(0)
        return re.sub(r'!\[[^\]]*\]\(([^)]+)\)', _check, text)

    final_output = _validate_inline_refs(final_output)
    all_new_artifacts = [a for a in all_new_artifacts if a in valid_set]
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

    return final_output, all_new_artifacts


@app.post("/api/analyze")
async def analyze(payload: dict):
    """HTTP endpoint: accepts {"question": "..."} and returns the full analysis with agent trace."""
    question = payload.get("question", "")
    history = payload.get("history")
    if not question:
        return JSONResponse(status_code=400, content={"error": "No question provided"})

    scope_error = _get_scope_error(question)
    if scope_error:
        trace = _finalize_trace(
            [
                {
                    "type": "agent_start",
                    "agent": "Orchestrator",
                    "ts": time.time(),
                },
                {
                    "type": "message",
                    "agent": "Orchestrator",
                    "content": scope_error,
                    "ts": time.time(),
                },
            ],
            "Orchestrator",
            scope_error,
        )
        return {
            "answer": scope_error,
            "artifacts": [],
            "trace": trace,
        }

    try:
        trace: list[dict] = []
        result, new_artifacts = await asyncio.wait_for(
            _run_pipeline(question, history, trace),
            timeout=PIPELINE_TIMEOUT_SECONDS,
        )

        return {
            "answer": result,
            "artifacts": new_artifacts,
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

            scope_error = _get_scope_error(question)
            if scope_error:
                await websocket.send_json({
                    "type": "result",
                    "content": scope_error,
                    "artifacts": [],
                })
                continue

            await websocket.send_json({
                "type": "status",
                "content": "Starting analysis pipeline...",
                "agent": "Orchestrator",
            })

            try:
                trace: list[dict] = []
                heartbeat_task = asyncio.create_task(_heartbeat(websocket))
                try:
                    final_output, new_artifacts = await asyncio.wait_for(
                        _run_pipeline(question, history, trace, websocket),
                        timeout=PIPELINE_TIMEOUT_SECONDS,
                    )
                finally:
                    heartbeat_task.cancel()

                await websocket.send_json({
                    "type": "result",
                    "content": final_output,
                    "artifacts": new_artifacts,
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
