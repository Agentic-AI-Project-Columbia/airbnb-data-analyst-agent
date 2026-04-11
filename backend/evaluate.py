"""
Multi-Model Evaluation Pipeline
================================
Standalone script to compare LLM models on the Airbnb multi-agent pipeline.

Usage:
    python evaluate.py                                    # Run all models, all questions
    python evaluate.py --models "google/gemini-2.5-pro"   # Single model smoke test
    python evaluate.py --questions 1                      # Single question
"""

import os
import sys
import json
import time
import asyncio
import re
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

sys.path.insert(0, os.path.dirname(__file__))

from openai import AsyncOpenAI
from agents import (
    Agent,
    Runner,
    ItemHelpers,
    ModelProvider,
    MultiProvider,
    OpenAIChatCompletionsModel,
    RunConfig,
    set_tracing_disabled,
)

set_tracing_disabled(True)

# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

@dataclass
class ModelSpec:
    model_id: str
    display_name: str
    provider_type: str  # "vertex" | "openrouter"
    cost_per_1k_input: float = 0.0   # USD
    cost_per_1k_output: float = 0.0  # USD


EVAL_MODELS: list[ModelSpec] = [
    # GCP Vertex AI
    ModelSpec("google/gemini-2.5-pro", "Gemini 2.5 Pro", "vertex", 0.00125, 0.005),
    ModelSpec("google/gemini-2.5-flash", "Gemini 2.5 Flash", "vertex", 0.00015, 0.0006),
    ModelSpec("google/gemini-2.0-flash", "Gemini 2.0 Flash", "vertex", 0.0001, 0.0004),
    # OpenRouter
    ModelSpec("openai/gpt-4.1", "GPT-4.1", "openrouter", 0.002, 0.008),
    ModelSpec("openai/gpt-4.1-nano", "GPT-4.1 Nano", "openrouter", 0.0001, 0.0004),
    ModelSpec("openai/gpt-5.4-mini", "GPT-5.4 Mini", "openrouter", 0.0005, 0.002),
    ModelSpec("anthropic/claude-sonnet-4-6", "Claude Sonnet 4.6", "openrouter", 0.003, 0.015),
    ModelSpec("anthropic/claude-opus-4-6", "Claude Opus 4.6", "openrouter", 0.015, 0.075),
]

EVAL_QUESTIONS = [
    {"id": 1, "category": "Pricing",      "question": "How does pricing vary by room type across the five boroughs?"},
    {"id": 2, "category": "Host Quality",  "question": "Do superhosts get better review scores than regular hosts?"},
    {"id": 3, "category": "Temporal",      "question": "How has host sign-up activity changed over the years?"},
    {"id": 4, "category": "Availability",  "question": "Which neighbourhoods have the highest and lowest availability throughout the year?"},
    {"id": 5, "category": "Reviews",       "question": "What are the most common complaints in guest reviews?"},
    {"id": 6, "category": "Geographic",    "question": "How does the density of listings compare across boroughs and what types dominate each area?"},
    {"id": 7, "category": "Amenities",     "question": "Do listings with more amenities charge higher prices and get better reviews?"},
]

STAGE_TIMEOUT = 180   # seconds per stage
PIPELINE_TIMEOUT = 420  # seconds total


# ---------------------------------------------------------------------------
# Provider factory
# ---------------------------------------------------------------------------

def _create_vertex_run_config() -> RunConfig:
    """Create a RunConfig for Vertex AI with a fresh GCP token."""
    import google.auth
    import google.auth.transport.requests

    gcp_project = os.environ.get("GCP_PROJECT_ID")
    gcp_location = os.environ.get("GCP_LOCATION", "us-central1")
    if not gcp_project:
        raise RuntimeError("GCP_PROJECT_ID not set")

    creds, _ = google.auth.default()
    creds.refresh(google.auth.transport.requests.Request())

    client = AsyncOpenAI(
        api_key=creds.token,
        base_url=(
            f"https://{gcp_location}-aiplatform.googleapis.com"
            f"/v1beta1/projects/{gcp_project}/locations/{gcp_location}"
            f"/endpoints/openapi"
        ),
    )

    class _VertexProvider(ModelProvider):
        def get_model(self, model_name: str):
            return OpenAIChatCompletionsModel(model=model_name, openai_client=client)

    return RunConfig(model_provider=_VertexProvider())


def _create_openrouter_run_config() -> RunConfig:
    """Create a RunConfig for OpenRouter."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    return RunConfig(
        model_provider=MultiProvider(
            openai_client=client,
            openai_prefix_mode="model_id",
            unknown_prefix_mode="model_id",
        )
    )


def create_run_config(spec: ModelSpec) -> RunConfig:
    if spec.provider_type == "vertex":
        return _create_vertex_run_config()
    elif spec.provider_type == "openrouter":
        return _create_openrouter_run_config()
    else:
        raise ValueError(f"Unknown provider: {spec.provider_type}")


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def create_agents(model_id: str) -> dict:
    """Create a fresh set of pipeline agents for the given model."""
    from agents import function_tool
    from prompts import load_prompt
    from tools.sql_runner import run_sql, get_schema_description
    from tools.code_executor import execute_python

    schema_desc = get_schema_description()

    collector_instructions = load_prompt("collector").format(SCHEMA_INFO=schema_desc)
    analyst_instructions = load_prompt("analyst").replace("{SCHEMA_INFO}", schema_desc)
    hypothesizer_instructions = load_prompt("hypothesizer")
    presenter_instructions = load_prompt("presenter")

    # ---- Tools (need unique names per agent set to avoid collisions) ----
    @function_tool
    def collector_query_db(sql: str) -> str:
        """Execute a SQL query against the NYC Airbnb DuckDB database."""
        return run_sql(sql)

    @function_tool
    def analyst_query_db(sql: str) -> str:
        """Execute a SQL query against the NYC Airbnb DuckDB database for iterative analysis."""
        return run_sql(sql)

    @function_tool
    def analyst_run_code(code: str) -> str:
        """Execute Python code for exploratory data analysis."""
        return execute_python(code)

    @function_tool
    def hyp_create_viz(code: str) -> str:
        """Execute Python code to generate data visualizations."""
        return execute_python(code)

    @function_tool
    def pres_create_viz(code: str) -> str:
        """Execute Python code to generate presentation-quality visualizations."""
        return execute_python(code)

    @function_tool
    def pres_query_db(sql: str) -> str:
        """Execute a SQL query against the NYC Airbnb DuckDB database."""
        return run_sql(sql)

    @function_tool
    def pres_run_code(code: str) -> str:
        """Execute Python code for data analysis."""
        return execute_python(code)

    # ---- Agents ----
    collector = Agent(
        name="Data Collector",
        instructions=collector_instructions,
        tools=[collector_query_db],
        model=model_id,
    )
    analyst = Agent(
        name="EDA Analyst",
        instructions=analyst_instructions,
        tools=[analyst_run_code, analyst_query_db],
        model=model_id,
    )
    hypothesizer = Agent(
        name="Hypothesis Generator",
        instructions=hypothesizer_instructions,
        tools=[hyp_create_viz],
        model=model_id,
    )

    # Presenter with sub-agents
    _pres_collector = Agent(
        name="Data Collector",
        instructions=(
            schema_desc + "\n\n"
            "You are assisting the Presenter agent. Run the SQL query needed to get "
            "the requested data, return the results, then hand off back to the Presenter."
        ),
        tools=[pres_query_db],
        model=model_id,
    )
    _pres_analyst = Agent(
        name="EDA Analyst",
        instructions=(
            "You are assisting the Presenter agent. Run the requested Python analysis, "
            "return the results, then hand off back to the Presenter.\n"
            "DATA_DIR and ARTIFACTS_DIR are pre-set variables available in your code."
        ),
        tools=[pres_run_code],
        model=model_id,
    )
    presenter = Agent(
        name="Presenter",
        instructions=presenter_instructions,
        tools=[pres_create_viz],
        handoffs=[_pres_collector, _pres_analyst],
        model=model_id,
    )
    _pres_collector.handoffs = [presenter]
    _pres_analyst.handoffs = [presenter]

    return {
        "collector": collector,
        "analyst": analyst,
        "hypothesizer": hypothesizer,
        "presenter": presenter,
    }


# ---------------------------------------------------------------------------
# Pipeline helpers (replicated from main.py, no imports from main)
# ---------------------------------------------------------------------------

def _build_collector_input(question: str) -> str:
    return (
        "Stage 1 of 4: Data Collection.\n"
        "Collect only the data needed to answer the request.\n"
        "Do not provide the final answer.\n\n"
        f"Resolved user request:\n{question}"
    )


def _build_analyst_input(question: str, collector_output: str) -> str:
    return (
        "Stage 2 of 4: Exploratory Data Analysis.\n"
        "Use the collected data below to compute findings, patterns, and caveats.\n"
        "Do not provide the final polished user answer yet.\n\n"
        f"Resolved user request:\n{question}\n\n"
        f"Collected data:\n{collector_output}"
    )


def _build_hypothesis_input(question: str, collector_output: str, analyst_output: str) -> str:
    return (
        "Stage 3 of 4: Hypothesis and visualization.\n"
        "Use the collected data and analyst findings to form a hypothesis with evidence.\n"
        "Generate visualizations to support key findings.\n"
        "Do not worry about polishing the final output - that happens next.\n\n"
        f"Resolved user request:\n{question}\n\n"
        f"Collected data:\n{collector_output}\n\n"
        f"Analyst findings:\n{analyst_output}"
    )


def _safe_truncate(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... ({len(text) - limit} chars truncated)"


def _build_presenter_input(question: str, collector_output: str, analyst_output: str,
                           hypothesis_output: str, chart_paths: list[str] | None = None) -> str:
    parts = [
        "Stage 4 of 4: Final presentation.\n"
        "Transform the analysis into a polished, insight-driven answer for the user.\n"
        "Do NOT add new analysis - just present what was found in the best possible way.\n\n"
        f"Original user question:\n{question}\n\n"
        f"Collected data (raw query results):\n{_safe_truncate(collector_output)}\n\n"
        f"Analyst findings:\n{analyst_output}\n\n"
        f"Hypothesis and evidence:\n{hypothesis_output}"
    ]
    if chart_paths:
        chart_list = "\n".join(f"  - {p}" for p in chart_paths)
        parts.append(
            f"\n\nCharts already generated by previous stages:\n{chart_list}\n"
            "Do NOT recreate these. Only create NEW presentation-quality visualizations "
            "that improve on these or add a different perspective. Aim for 2-3 charts total."
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
# Pipeline runner with metrics
# ---------------------------------------------------------------------------

@dataclass
class StageMetrics:
    name: str
    time_s: float = 0.0
    tool_calls: int = 0
    agent_steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    artifacts: list = field(default_factory=list)
    error: str | None = None


@dataclass
class EvalResult:
    model_id: str
    model_name: str
    provider: str
    question_id: int
    category: str
    question: str
    status: str = "pending"
    total_time_s: float = 0.0
    answer_len: int = 0
    answer_preview: str = ""
    num_charts: int = 0
    num_tool_calls: int = 0
    num_agent_steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    quality_score: int = 0
    artifacts: list = field(default_factory=list)
    stages: list = field(default_factory=list)
    error: str | None = None


def _extract_artifacts_from_output(output: str) -> list[str]:
    """Extract artifact paths from tool output JSON."""
    arts = []
    try:
        parsed = json.loads(output)
        if isinstance(parsed, dict) and "artifacts" in parsed:
            for a in parsed["artifacts"]:
                path = a.get("path") if isinstance(a, dict) else a if isinstance(a, str) else None
                if path:
                    arts.append(path)
    except (json.JSONDecodeError, TypeError):
        pass
    return arts


async def _run_stage(agent, stage_input: str, run_config: RunConfig) -> tuple[str, StageMetrics]:
    """Run a single agent stage, collecting metrics."""
    metrics = StageMetrics(name=agent.name)
    t0 = time.time()

    try:
        result = Runner.run_streamed(agent, input=stage_input, run_config=run_config)

        async for event in result.stream_events():
            if event.type == "agent_updated_stream_event":
                metrics.agent_steps += 1
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    metrics.tool_calls += 1
                elif event.item.type == "tool_call_output_item":
                    output = str(event.item.output) if event.item.output else ""
                    metrics.artifacts.extend(_extract_artifacts_from_output(output))
                elif event.item.type == "message_output_item":
                    metrics.agent_steps += 1

        # Extract token usage from raw responses
        if hasattr(result, 'raw_responses'):
            for resp in result.raw_responses:
                usage = getattr(resp, 'usage', None)
                if usage:
                    metrics.input_tokens += getattr(usage, 'input_tokens', 0) or 0
                    metrics.output_tokens += getattr(usage, 'output_tokens', 0) or 0

        final_output = result.final_output
        final_text = "" if final_output is None else str(final_output)

    except Exception as e:
        final_text = ""
        metrics.error = str(e)

    metrics.time_s = time.time() - t0
    return final_text, metrics


async def run_eval_pipeline(agents: dict, run_config: RunConfig, question: str) -> tuple[str, list[StageMetrics]]:
    """Run the full 4-stage evaluation pipeline."""
    all_metrics: list[StageMetrics] = []

    # Stage 1: Data Collection
    print("    Stage 1/4: Data Collector...", end=" ", flush=True)
    collector_output, m1 = await asyncio.wait_for(
        _run_stage(agents["collector"], _build_collector_input(question), run_config),
        timeout=STAGE_TIMEOUT,
    )
    all_metrics.append(m1)
    print(f"done ({m1.time_s:.1f}s, {m1.tool_calls} calls)")

    # Stage 2: EDA Analysis
    print("    Stage 2/4: EDA Analyst...", end=" ", flush=True)
    analyst_output, m2 = await asyncio.wait_for(
        _run_stage(agents["analyst"], _build_analyst_input(question, collector_output), run_config),
        timeout=STAGE_TIMEOUT,
    )
    all_metrics.append(m2)
    print(f"done ({m2.time_s:.1f}s, {m2.tool_calls} calls)")

    # Stage 3: Hypothesis Generation
    print("    Stage 3/4: Hypothesis Generator...", end=" ", flush=True)
    hypothesis_output, m3 = await asyncio.wait_for(
        _run_stage(agents["hypothesizer"], _build_hypothesis_input(question, collector_output, analyst_output), run_config),
        timeout=STAGE_TIMEOUT,
    )
    all_metrics.append(m3)
    print(f"done ({m3.time_s:.1f}s, {m3.tool_calls} calls)")

    # Stage 4: Presentation
    chart_paths = []
    for m in all_metrics:
        chart_paths.extend([a for a in m.artifacts if re.search(r'\.(png|jpe?g|svg)$', a, re.IGNORECASE)])

    print("    Stage 4/4: Presenter...", end=" ", flush=True)
    final_output, m4 = await asyncio.wait_for(
        _run_stage(
            agents["presenter"],
            _build_presenter_input(question, collector_output, analyst_output, hypothesis_output, chart_paths or None),
            run_config,
        ),
        timeout=STAGE_TIMEOUT,
    )
    all_metrics.append(m4)
    print(f"done ({m4.time_s:.1f}s, {m4.tool_calls} calls)")

    return final_output, all_metrics


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_result(result: EvalResult, all_times: list[float] | None = None) -> int:
    """Compute a 0-100 quality score based on heuristic metrics."""
    score = 0

    # Success (25 points)
    if result.status == "success":
        score += 25

    # Charts (25 points): 0 charts=0, 1=10, 2=18, 3+=25
    chart_score = min(result.num_charts * 8.3, 25)
    score += int(chart_score)

    # Answer length (20 points): 0-500=5, 500-1500=12, 1500+=20
    if result.answer_len >= 1500:
        score += 20
    elif result.answer_len >= 500:
        score += 12
    elif result.answer_len > 0:
        score += 5

    # Efficiency (15 points): tool calls 3-12 is ideal
    if 3 <= result.num_tool_calls <= 12:
        score += 15
    elif result.num_tool_calls > 0:
        score += 8

    # Speed (15 points): relative to group
    if all_times and result.total_time_s > 0:
        max_time = max(all_times) if all_times else result.total_time_s
        if max_time > 0:
            speed_ratio = 1 - (result.total_time_s / max_time)
            score += int(speed_ratio * 15)
    elif result.total_time_s < 120:
        score += 15
    elif result.total_time_s < 200:
        score += 10

    return min(score, 100)


def estimate_cost(spec: ModelSpec, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1000) * spec.cost_per_1k_input + (output_tokens / 1000) * spec.cost_per_1k_output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def print_results_table(results: list[EvalResult]):
    """Print a formatted comparison table."""
    print("\n" + "=" * 120)
    print("MODEL EVALUATION RESULTS")
    print("=" * 120)

    # Group by model
    models = {}
    for r in results:
        if r.model_name not in models:
            models[r.model_name] = []
        models[r.model_name].append(r)

    # Header
    q_ids = sorted(set(r.question_id for r in results))
    header = f"{'Model':<25} | {'Provider':<12}"
    for qid in q_ids:
        header += f" | Q{qid} Time | Q{qid} Charts"
    header += f" | {'Avg Score':>9} | {'Est. Cost':>9} | {'Tokens':>10}"
    print(header)
    print("-" * len(header))

    for model_name, model_results in models.items():
        row = f"{model_name:<25} | {model_results[0].provider:<12}"
        total_score = 0
        total_cost = 0.0
        total_tokens = 0
        count = 0
        for qid in q_ids:
            qr = next((r for r in model_results if r.question_id == qid), None)
            if qr:
                if qr.status == "success":
                    row += f" | {qr.total_time_s:>6.0f}s | {qr.num_charts:>9}"
                else:
                    row += f" | {'FAIL':>7} | {'-':>9}"
                total_score += qr.quality_score
                total_cost += qr.estimated_cost_usd
                total_tokens += qr.input_tokens + qr.output_tokens
                count += 1
            else:
                row += f" | {'-':>7} | {'-':>9}"

        avg_score = total_score / count if count else 0
        row += f" | {avg_score:>9.0f} | ${total_cost:>8.4f} | {total_tokens:>10,}"
        print(row)

    print("=" * 120)

    # Per-model summaries
    print("\nDETAILED PER-MODEL SUMMARY:")
    print("-" * 80)
    for model_name, model_results in models.items():
        successes = [r for r in model_results if r.status == "success"]
        print(f"\n  {model_name} ({model_results[0].provider})")
        print(f"    Success rate: {len(successes)}/{len(model_results)}")
        if successes:
            avg_time = sum(r.total_time_s for r in successes) / len(successes)
            avg_charts = sum(r.num_charts for r in successes) / len(successes)
            avg_len = sum(r.answer_len for r in successes) / len(successes)
            total_in = sum(r.input_tokens for r in successes)
            total_out = sum(r.output_tokens for r in successes)
            total_cost = sum(r.estimated_cost_usd for r in successes)
            avg_score = sum(r.quality_score for r in successes) / len(successes)
            print(f"    Avg time: {avg_time:.1f}s | Avg charts: {avg_charts:.1f} | Avg answer: {avg_len:.0f} chars")
            print(f"    Tokens: {total_in:,} in + {total_out:,} out | Cost: ${total_cost:.4f}")
            print(f"    Avg quality score: {avg_score:.0f}/100")
        for r in model_results:
            status_icon = "OK" if r.status == "success" else "FAIL"
            print(f"    [{status_icon}] Q{r.question_id} ({r.category}): {r.total_time_s:.1f}s, "
                  f"{r.num_charts} charts, {r.num_tool_calls} tool calls, score={r.quality_score}")
            if r.error:
                print(f"         Error: {r.error[:100]}")


async def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM models on Airbnb analysis pipeline")
    parser.add_argument("--models", nargs="*", help="Model IDs to test (default: all)")
    parser.add_argument("--questions", nargs="*", type=int, help="Question IDs to test (default: all)")
    parser.add_argument("--output", default="evaluation_results.json", help="Output JSON file")
    args = parser.parse_args()

    # Filter models and questions
    models_to_test = EVAL_MODELS
    if args.models:
        models_to_test = [m for m in EVAL_MODELS if m.model_id in args.models]
        if not models_to_test:
            print(f"No matching models found. Available: {[m.model_id for m in EVAL_MODELS]}")
            return

    questions_to_test = EVAL_QUESTIONS
    if args.questions:
        questions_to_test = [q for q in EVAL_QUESTIONS if q["id"] in args.questions]

    print(f"\nEvaluation: {len(models_to_test)} models x {len(questions_to_test)} questions = {len(models_to_test) * len(questions_to_test)} runs")
    print(f"Models: {[m.display_name for m in models_to_test]}")
    print(f"Questions: {[q['category'] for q in questions_to_test]}\n")

    all_results: list[EvalResult] = []
    total_start = time.time()

    for spec in models_to_test:
        print(f"\n{'='*60}")
        print(f"MODEL: {spec.display_name} ({spec.model_id})")
        print(f"Provider: {spec.provider_type}")
        print(f"{'='*60}")

        # Create provider
        try:
            run_config = create_run_config(spec)
        except Exception as e:
            print(f"  SKIP: Failed to create provider: {e}")
            for q in questions_to_test:
                r = EvalResult(
                    model_id=spec.model_id, model_name=spec.display_name,
                    provider=spec.provider_type, question_id=q["id"],
                    category=q["category"], question=q["question"],
                    status="error", error=f"Provider setup failed: {e}",
                )
                all_results.append(r)
            continue

        # Create agents
        try:
            agents = create_agents(spec.model_id)
        except Exception as e:
            print(f"  SKIP: Failed to create agents: {e}")
            continue

        for q in questions_to_test:
            print(f"\n  Q{q['id']} [{q['category']}]: {q['question'][:60]}...")

            result = EvalResult(
                model_id=spec.model_id, model_name=spec.display_name,
                provider=spec.provider_type, question_id=q["id"],
                category=q["category"], question=q["question"],
            )

            t0 = time.time()
            try:
                final_output, stage_metrics = await asyncio.wait_for(
                    run_eval_pipeline(agents, run_config, q["question"]),
                    timeout=PIPELINE_TIMEOUT,
                )

                result.status = "success"
                result.total_time_s = time.time() - t0
                result.answer_len = len(final_output)
                result.answer_preview = final_output[:300]

                # Aggregate stage metrics
                all_artifacts = []
                result.stages = []
                for sm in stage_metrics:
                    result.num_tool_calls += sm.tool_calls
                    result.num_agent_steps += sm.agent_steps
                    result.input_tokens += sm.input_tokens
                    result.output_tokens += sm.output_tokens
                    all_artifacts.extend(sm.artifacts)
                    result.stages.append(asdict(sm))
                    if sm.error:
                        result.error = (result.error or "") + f"{sm.name}: {sm.error}; "

                image_artifacts = [a for a in all_artifacts if re.search(r'\.(png|jpe?g|svg)$', a, re.IGNORECASE)]
                result.num_charts = len(image_artifacts)
                result.artifacts = all_artifacts
                result.estimated_cost_usd = estimate_cost(spec, result.input_tokens, result.output_tokens)

                print(f"  -> SUCCESS: {result.total_time_s:.1f}s, {result.num_charts} charts, "
                      f"{result.num_tool_calls} tool calls, {result.answer_len} chars, "
                      f"{result.input_tokens + result.output_tokens:,} tokens, "
                      f"${result.estimated_cost_usd:.4f}")

            except asyncio.TimeoutError:
                result.status = "timeout"
                result.total_time_s = time.time() - t0
                result.error = f"Pipeline timed out after {PIPELINE_TIMEOUT}s"
                print(f"  -> TIMEOUT after {result.total_time_s:.1f}s")

            except Exception as e:
                result.status = "error"
                result.total_time_s = time.time() - t0
                result.error = str(e)
                print(f"  -> ERROR: {str(e)[:120]}")

            all_results.append(result)

            # Save intermediate results
            _save_results(all_results, args.output, total_start)

    # Final scoring (needs all times for relative speed scoring)
    all_times = [r.total_time_s for r in all_results if r.status == "success"]
    for r in all_results:
        r.quality_score = score_result(r, all_times)

    _save_results(all_results, args.output, total_start)
    print_results_table(all_results)

    total_duration = time.time() - total_start
    print(f"\nTotal evaluation time: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    print(f"Results saved to: {args.output}")


def _save_results(results: list[EvalResult], output_path: str, start_time: float):
    """Save results to JSON."""
    # Group by model
    models_data = {}
    for r in results:
        if r.model_id not in models_data:
            models_data[r.model_id] = {
                "model_id": r.model_id,
                "display_name": r.model_name,
                "provider": r.provider,
                "results": [],
            }
        models_data[r.model_id]["results"].append({
            "question_id": r.question_id,
            "category": r.category,
            "question": r.question,
            "status": r.status,
            "total_time_s": round(r.total_time_s, 1),
            "answer_len": r.answer_len,
            "answer_preview": r.answer_preview,
            "num_charts": r.num_charts,
            "num_tool_calls": r.num_tool_calls,
            "num_agent_steps": r.num_agent_steps,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "estimated_cost_usd": round(r.estimated_cost_usd, 6),
            "quality_score": r.quality_score,
            "artifacts": r.artifacts,
            "stages": r.stages if hasattr(r, 'stages') else [],
            "error": r.error,
        })

    # Compute model summaries
    for model_data in models_data.values():
        successes = [r for r in model_data["results"] if r["status"] == "success"]
        model_data["summary"] = {
            "success_rate": len(successes) / len(model_data["results"]) if model_data["results"] else 0,
            "avg_time_s": round(sum(r["total_time_s"] for r in successes) / len(successes), 1) if successes else 0,
            "avg_score": round(sum(r["quality_score"] for r in successes) / len(successes), 1) if successes else 0,
            "avg_charts": round(sum(r["num_charts"] for r in successes) / len(successes), 1) if successes else 0,
            "total_cost_usd": round(sum(r["estimated_cost_usd"] for r in successes), 6),
            "total_input_tokens": sum(r["input_tokens"] for r in successes),
            "total_output_tokens": sum(r["output_tokens"] for r in successes),
        }

    output = {
        "metadata": {
            "run_date": datetime.now(timezone.utc).isoformat(),
            "total_duration_s": round(time.time() - start_time, 1),
            "num_models": len(models_data),
            "num_questions": len(set(r.question_id for r in results)),
            "questions": [{"id": q["id"], "category": q["category"], "question": q["question"]} for q in EVAL_QUESTIONS],
        },
        "models": list(models_data.values()),
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
