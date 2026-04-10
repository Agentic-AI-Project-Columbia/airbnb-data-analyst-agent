# Airbnb Multi-Agent Data Analyst

A production-grade, multi-agent data analysis system that turns natural language questions about NYC Airbnb data into polished, insight-driven reports with visualizations — fully automated from query to presentation.

Built with the **OpenAI Agents SDK**, **DuckDB**, **FastAPI**, and **Next.js 16**. Deployed on **Google Cloud Run**.

**Stack:** Python 3.12 | TypeScript | React 19 | Tailwind CSS 4 | WebSocket | Docker

---

## Demo

![Application Screenshot](FireShot%20Capture%20002%20-%20Airbnb%20Data%20Analyst%20-%20localhost.png)

*A single question triggers a four-stage agent pipeline. The user sees real-time progress, then receives a narrative answer with presentation-quality charts and a full execution trace.*

---

## What This Project Does

A user types a question like *"Which neighbourhoods have the highest prices for entire homes?"* and the system:

1. **Translates** the question into SQL and queries a 37K-row listings dataset via DuckDB
2. **Analyzes** the results with dynamically generated Python (pandas, scipy, numpy)
3. **Hypothesizes** — forms data-grounded conclusions and generates analytical charts
4. **Presents** — rewrites everything into a polished briefing with annotated, publication-ready visualizations

All four stages run autonomously. Each agent writes its own code, executes it in a sandboxed subprocess, inspects the output, and passes structured context to the next stage. The frontend streams every step in real time over WebSocket.

---

## Architecture

```
User Question
     |
     v
+--------------+
| Orchestrator | --- coordinates the pipeline
+------+-------+
       |
       +---> Data Collector ---> DuckDB (SQL on CSVs)
       |          |
       |          v  (query results)
       +---> EDA Analyst ---> Python Code Executor
       |          |
       |          v  (statistical findings)
       +---> Hypothesis Generator ---> Python Code Executor (analytical charts)
       |          |
       |          v  (hypothesis + evidence)
       +---> Presenter ---> Python Code Executor (presentation charts)
                  |
                  v
         Polished Answer + Visualizations
```

**Five agents. Three tools. One pipeline.**

Each agent is a distinct `Agent` object from the OpenAI Agents SDK with its own system prompt, tools, and structured output schema. The orchestrator hands off sequentially, threading each stage's output as context to the next.

---

## Key Technical Highlights

| Area | Details |
|------|---------|
| **Agent Orchestration** | Handoff-based multi-agent coordination using the OpenAI Agents SDK — not simple function calling, but autonomous agents that write and execute arbitrary code |
| **Dynamic Code Generation** | Agents write SQL and Python at runtime, tailored to each question. No templates or predefined queries |
| **Sandboxed Execution** | Python runs in isolated subprocesses with a 120s timeout, restricted imports, and automatic artifact capture |
| **Real-Time Streaming** | WebSocket streams every agent action (handoffs, tool calls, outputs) to the frontend as it happens |
| **Execution Trace UI** | Expandable four-stage timeline showing SQL queries, Python code, data previews, and agent reasoning |
| **Interactive Schema Explorer** | Frontend fetches live schema from DuckDB and lets users browse table structures before asking questions |
| **Production Deployment** | Dockerized frontend + backend deployed to GCP Cloud Run via Cloud Build CI/CD pipeline |
| **Type Safety** | Full TypeScript frontend with strict types; Pydantic models for backend data contracts |

---

## Implemented Features

### Core Requirements

| # | Requirement | Status | Implementation |
|---|------------|--------|----------------|
| 1 | **Frontend** | Done | Next.js 16 / React 19 app with real-time chat, markdown rendering, inline chart display, schema explorer, and agent trace panel |
| 2 | **Agent Framework** | Done | OpenAI Agents SDK (`openai-agents`) — `Agent`, `function_tool`, `Runner.run_streamed()`, `handoffs` |
| 3 | **Tool Calling** | Done | Three tools: `query_database` (SQL), `run_analysis_code` (Python EDA), `create_visualization` (charts) |
| 4 | **Non-Trivial Dataset** | Done | NYC Airbnb: 37K listings (71 columns), 985K reviews, 230 neighbourhoods |
| 5 | **Multi-Agent Pattern** | Done | 5-agent orchestrator-handoff pipeline: Orchestrator -> Collector -> Analyst -> Hypothesizer -> Presenter |
| 6 | **Deployment** | Done | GCP Cloud Run (Docker containers, Cloud Build CI/CD, Artifact Registry) |
| 7 | **README** | Done | This file |

### Elective Features (Grab Bag)

| # | Feature | Points | Status | Where |
|---|---------|--------|--------|-------|
| 1 | **Code Execution** | 2.5 | Done | `backend/tools/code_executor.py` — sandboxed subprocess with artifact capture, 120s timeout, import restrictions |
| 2 | **Data Visualization** | 2.5 | Done | Hypothesis Generator + Presenter agents write matplotlib/seaborn code to generate analytical and presentation-quality charts |
| 3 | **Structured Output** | Bonus | Done | `backend/models/schemas.py` — Pydantic models (`QueryResult`, `EDAFindings`) for typed inter-agent data flow |
| 4 | **Agent Thinking Trace** | Bonus | Done | `ThinkingTrace.tsx` — collapsible execution timeline with 4 stages, SQL/Python blocks, data previews, and timing |

### Additional Features (Beyond Requirements)

| Feature | Description |
|---------|-------------|
| **Real-Time WebSocket Streaming** | Every agent action streams to the frontend as it happens — no waiting for the full pipeline to finish |
| **Pipeline Progress Flowchart** | Visual 4-stage progress indicator shows which agent is active during analysis |
| **Interactive Schema Explorer** | Users can browse all table schemas (columns, types, row counts) before asking questions |
| **Dataset Overview Dashboard** | Landing page shows live statistics pulled from DuckDB (row counts, column counts) |
| **Share Button** | Copy analysis results (question + answer + chart links) to clipboard or share via Web Share API |
| **Single Q&A Flow** | Clean question-answer UX with "New Question" reset to prevent stale context accumulation |
| **Suggested Questions** | Curated questions with category labels guide users toward meaningful analysis |
| **Memory Game** | Interactive waiting experience while the pipeline processes |
| **Agent Retry on Failure** | Code execution failures trigger automatic re-attempts with error context |
| **SQL Table Highlighting** | SQL queries in the trace highlight table names as clickable schema popovers |

---

## The Pipeline in Detail

### Stage 1: Collect

| Component | Location |
|-----------|----------|
| Agent | `backend/agent_defs/collector.py` |
| Tool | `backend/tools/sql_runner.py` -> `run_sql()` |
| Engine | DuckDB (in-memory, reads CSVs natively) |

The Data Collector translates natural language into DuckDB SQL at runtime. It queries three registered views — **listings** (37K rows, 71 columns), **reviews** (985K rows), and **neighbourhoods** (230 rows) — with aggregations, filters, and joins tailored to each question.

### Stage 2: Analyze (EDA)

| Component | Location |
|-----------|----------|
| Agent | `backend/agent_defs/analyst.py` |
| Tool | `backend/tools/code_executor.py` -> `execute_python()` |

The EDA Analyst writes and executes Python code (pandas, numpy, scipy, duckdb) to compute statistics, segment data, identify correlations, and surface quantitative findings. Different questions produce different code and different analyses.

### Stage 3: Hypothesize

| Component | Location |
|-----------|----------|
| Agent | `backend/agent_defs/hypothesizer.py` |
| Tool | `backend/tools/code_executor.py` -> `execute_python()` |

Takes EDA findings and forms data-grounded hypotheses. Writes matplotlib/seaborn code to generate analytical charts — breakdowns by dimension, distributions, comparisons, and outlier analysis. Charts saved as PNG artifacts.

### Stage 4: Present

| Component | Location |
|-----------|----------|
| Agent | `backend/agent_defs/presenter.py` |
| Tool | `backend/tools/code_executor.py` -> `execute_python()` |

Transforms the full pipeline output into a polished briefing for non-technical audiences. Generates presentation-quality charts with annotated values, insight-driven titles, and a professional color palette. Weaves visuals into a concise narrative.

---

## Tech Stack

### Backend
- **Python 3.12** with FastAPI and Uvicorn (async)
- **OpenAI Agents SDK** (`openai-agents >=0.7.0`) for agent orchestration
- **DuckDB** for fast analytical SQL on CSV data
- **pandas / numpy / scipy** for data analysis
- **matplotlib / seaborn** for visualization
- **Pydantic** for data validation and structured output
- **uv** for fast dependency management

### Frontend
- **Next.js 16.2** with React 19 and TypeScript 5
- **Tailwind CSS 4** for styling
- **react-markdown** with remark-gfm for rich content rendering
- **WebSocket** for real-time streaming

### Infrastructure
- **Docker** multi-stage builds for both services
- **Google Cloud Run** for serverless deployment
- **Cloud Build** for CI/CD pipeline
- **Artifact Registry** for container images

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- An OpenAI API key or an OpenRouter API key

### Local Development

```bash
# 1. Clone and enter the project
cd airbnb

# 2. Backend
cd backend
cp .env.example .env          # Add your OPENAI_API_KEY or OPENROUTER_API_KEY
uv sync                       # Install dependencies
uv run python main.py         # Starts at http://localhost:8000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                   # Starts at http://localhost:3000
```

### Docker

```bash
# Set your API key
export OPENAI_API_KEY=sk-...
# or: export OPENROUTER_API_KEY=sk-or-...

docker-compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

### GCP Cloud Run

The project includes a full Cloud Build pipeline (`cloudbuild.yaml`) that:
1. Pulls data from a GCS bucket
2. Builds and pushes both Docker images to Artifact Registry
3. Deploys both services to Cloud Run with proper resource allocation

```bash
gcloud builds submit --config=cloudbuild.yaml
```

---

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/schema` | GET | Returns DuckDB schema (tables, columns, types, row counts) |
| `/api/analyze` | POST | Synchronous analysis — `{"question": "...", "history": [...]}` |
| `/ws/analyze` | WebSocket | Streaming analysis with real-time trace events |

### WebSocket Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `status` | Server -> Client | Progress update with agent name |
| `trace` | Server -> Client | Agent execution step (handoff, tool call, output) |
| `result` | Server -> Client | Final answer with markdown content and artifact paths |
| `error` | Server -> Client | Error message |

---

## Project Structure

```
airbnb/
|-- backend/
|   |-- main.py                    # FastAPI app, HTTP + WebSocket endpoints, pipeline orchestration
|   |-- agent_defs/
|   |   |-- orchestrator.py        # Orchestrator agent (handoff routing)
|   |   |-- collector.py           # Data Collector agent + query_database tool
|   |   |-- analyst.py             # EDA Analyst agent + run_analysis_code tool
|   |   |-- hypothesizer.py        # Hypothesis Generator agent + create_visualization tool
|   |   |-- presenter.py           # Presenter agent + create_visualization tool
|   |   +-- config.py              # Model configuration (OpenAI / OpenRouter)
|   |-- tools/
|   |   |-- sql_runner.py          # DuckDB connection, view registration, SQL execution
|   |   +-- code_executor.py       # Sandboxed Python execution with artifact capture
|   |-- models/
|   |   +-- schemas.py             # Pydantic structured output models
|   |-- artifacts/                 # Generated charts and outputs (runtime)
|   |-- Dockerfile
|   |-- pyproject.toml
|   +-- .env.example
|-- frontend/
|   |-- src/
|   |   |-- app/
|   |   |   |-- layout.tsx         # Root layout with fonts
|   |   |   |-- page.tsx           # Main page — landing, Q&A flow, WebSocket logic
|   |   |   +-- globals.css        # Design system and animations
|   |   |-- components/
|   |   |   |-- Header.tsx          # App header with New Question button
|   |   |   |-- ChatInput.tsx       # Text input with send button
|   |   |   |-- MessageBubble.tsx   # Message renderer (markdown, charts, share, trace)
|   |   |   |-- ThinkingTrace.tsx   # Expandable agent execution timeline
|   |   |   |-- PipelineFlowchart.tsx # Visual pipeline progress indicator
|   |   |   |-- DataOverview.tsx    # Dataset statistics dashboard
|   |   |   |-- SchemaExplorer.tsx  # Interactive table schema browser
|   |   |   |-- SqlQueryBlock.tsx   # SQL display with clickable table names
|   |   |   |-- QueryResultSummary.tsx # Data preview tables in trace
|   |   |   +-- WaitingGame.tsx     # Memory game during analysis
|   |   +-- lib/
|   |       +-- pipeline-stages.ts  # Stage definitions and agent-to-stage mapping
|   |-- Dockerfile
|   +-- package.json
|-- Sample Data/
|   |-- listings.csv               # ~37K listings, 71 columns (~85 MB)
|   |-- reviews.csv                # ~985K reviews, 6 columns (~295 MB)
|   +-- neighbourhoods.csv         # 230 neighbourhoods, 2 columns
|-- docker-compose.yml
|-- cloudbuild.yaml                # GCP Cloud Build CI/CD pipeline
+-- README.md
```

---

## Dataset

[Inside Airbnb](http://insideairbnb.com/) — New York City (2022 scrape).

| Table | Rows | Columns | Description |
|-------|------|---------|-------------|
| **listings** | ~37,000 | 71 | Host info, location, property type, room type, pricing, amenities, availability, review scores |
| **reviews** | ~985,000 | 6 | Review ID, listing ID, date, reviewer info, free-text comments |
| **neighbourhoods** | 230 | 2 | Neighbourhood names mapped to boroughs (Manhattan, Brooklyn, Queens, Bronx, Staten Island) |

---

## Skills Demonstrated

- **Agentic AI system design** — multi-agent orchestration with handoffs, context threading, and autonomous code generation
- **Full-stack development** — Python backend + TypeScript/React frontend with real-time WebSocket communication
- **Data engineering** — DuckDB analytical queries, pandas pipelines, automated visualization generation
- **Production deployment** — Dockerized microservices on GCP Cloud Run with CI/CD
- **Frontend engineering** — React 19, streaming UI updates, interactive schema explorer, responsive design
- **System design** — clean separation of concerns, sandboxed execution, structured inter-agent contracts, error recovery
