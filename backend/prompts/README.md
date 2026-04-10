# Agent System Prompts

This folder contains every system prompt used in the multi-agent pipeline. Each `.md` file is the **single source of truth** for its agent — the backend loads these files directly at startup, so the prompt text you read here is exactly what the LLM receives.

## Pipeline Overview

The system uses a 4-stage sequential handoff pipeline built on the **OpenAI Agents SDK** (`openai-agents>=0.7.0`). Each agent receives a system prompt that defines its role, tools, and output contract.

```
User Question
     |
     v
 Orchestrator  (orchestrator.md)
     |
     +---> Stage 1: Data Collector   (collector.md)  --> DuckDB SQL
     +---> Stage 2: EDA Analyst      (analyst.md)    --> Python (pandas, numpy, scipy)
     +---> Stage 3: Hypothesis Gen.  (hypothesizer.md) --> Python (matplotlib, seaborn)
     +---> Stage 4: Presenter        (presenter.md)  --> Python (matplotlib, seaborn)
     |
     v
 Final Answer + Charts
```

## Prompt Files

| File | Agent | What the Prompt Instructs | Key Libraries Referenced |
|------|-------|--------------------------|--------------------------|
| [orchestrator.md](orchestrator.md) | Orchestrator | Sequencing rules for the 4-stage pipeline; when to hand off and what context to pass | `openai-agents` (handoff routing) |
| [collector.md](collector.md) | Data Collector | How to translate natural language into DuckDB SQL; schema awareness, join relationships, query guidelines | `duckdb>=1.2.0` |
| [analyst.md](analyst.md) | EDA Analyst | Statistical analysis strategy; what metrics to compute, how to segment data, output format for downstream agents | `pandas>=2.2.0`, `numpy>=1.26.0`, `scipy>=1.14.0`, `duckdb` |
| [hypothesizer.md](hypothesizer.md) | Hypothesis Generator | Deep-dive analysis strategy; how to go beyond surface findings, visualization guidelines, error retry protocol | `matplotlib>=3.9.0`, `seaborn>=0.13.0`, `duckdb` |
| [presenter.md](presenter.md) | Presenter | Briefing format and style rules; chart design standards (Airbnb color palette, annotation guidelines), output structure | `matplotlib>=3.9.0`, `seaborn>=0.13.0` |

## Prompt Engineering Decisions

### Agent Specialization
Each prompt is scoped to a single responsibility. The Collector is explicitly told *not* to provide conclusions. The Analyst is told to focus on analysis, *not* visualization. The Presenter is told *never* to include code. This prevents agents from overstepping their role and ensures each stage adds distinct value.

### Context Threading
The Orchestrator prompt enforces that all prior results are passed forward at each handoff. This means the Presenter has access to raw SQL, statistical findings, *and* the hypothesis — enabling it to produce a coherent narrative grounded in every stage's output.

### Code Execution Guardrails
The Hypothesizer and Presenter prompts include identical error-handling protocols: check `exit_code`, read `stderr`, fix the code, retry up to 3 times, and never paste failed code into the final output. This was added after observing that LLMs will dump raw Python into their text response when execution fails — the prompt explicitly prohibits this for the non-technical audience.

### Dynamic Schema Injection
The Collector prompt contains a `{SCHEMA_INFO}` placeholder that gets filled at startup with the live database schema (table names, column names, types, row counts) generated from DuckDB via `duckdb>=1.2.0`. This means the agent always has an accurate picture of the data, even if tables or columns change.

### Visualization Standards
Both the Hypothesizer and Presenter prompts specify chart design rules (font sizes, color palettes, annotation patterns, layout settings). The Presenter's guidelines are more stringent — it targets a non-technical audience with insight-driven titles like *"Manhattan charges 40% more than Brooklyn"* rather than generic labels like *"Average Price by Borough"*.

## File Format

Each `.md` file has two sections:

1. **YAML frontmatter** (between `---` lines) — metadata only, stripped by the loader before the prompt is sent to the LLM. Documents the agent name, a description, and any runtime variables.

2. **Prompt body** — the exact system instruction text. What you read is what the model receives.

## How Changes Propagate

The prompts are loaded by `backend/prompts/__init__.py` at Python import time. The loader is ~10 lines:

```python
def load_prompt(name: str) -> str:
    text = (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    return text.strip()
```

Each agent definition file (e.g., `backend/agent_defs/collector.py`) calls `load_prompt("collector")` and passes the result to the OpenAI Agents SDK `Agent()` constructor. Editing a prompt file and restarting the server is all that's needed — no code changes required.
