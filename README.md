# Airbnb Multi-Agent Data Analyst

A multi-agent system that performs the first three steps of a data analysis lifecycle on NYC Airbnb data: **Collect**, **Explore (EDA)**, and **Hypothesize**.

Built with the **OpenAI Agents SDK**, **DuckDB**, **FastAPI**, and **Next.js**.

---

## Architecture

```
User Question
     │
     ▼
┌─────────────┐
│ Orchestrator │ ─── coordinates the pipeline
└──────┬──────┘
       │
       ├──► Data Collector ──► DuckDB (SQL on CSVs)
       │         │
       │         ▼ (query results)
       ├──► EDA Analyst ──► Python Code Executor
       │         │
       │         ▼ (statistical findings)
       └──► Hypothesis Generator ──► Python Code Executor (charts)
                  │
                  ▼
         Hypothesis + Visualizations
```

Four agents, three tools, one pipeline.

---

## The Three Steps

### Step 1: Collect

| What | Where |
|------|-------|
| Agent | `backend/agent_defs/collector.py` → `collector_agent` |
| Tool | `backend/tools/sql_runner.py` → `run_sql()` |
| Data Engine | DuckDB (in-memory, reads `.csv` and `.csv.gz` natively) |

The **Data Collector** agent translates the user's question into one or more DuckDB SQL queries at runtime. It queries five registered views:

- **calendar** — 13.3M rows of daily availability and pricing
- **listings** — 36,445 listings with 85 columns (host, location, pricing, reviews, amenities)
- **listings_summary** — compact 19-column listing view
- **reviews** — 1M+ reviews with dates spanning 2009–2026
- **neighbourhoods** — NYC neighbourhood names and groupings

The agent writes dynamic SQL with aggregations, filters, and joins tailored to each question. Results are returned as JSON.

### Step 2: Explore / EDA

| What | Where |
|------|-------|
| Agent | `backend/agent_defs/analyst.py` → `analyst_agent` |
| Tool | `backend/tools/code_executor.py` → `execute_python()` |

The **EDA Analyst** agent receives collected data and writes Python code (pandas, numpy, scipy, duckdb) that it executes at runtime. It computes statistics, segments data, identifies correlations and anomalies, and surfaces specific quantitative findings. Different questions produce different code and different analyses.

### Step 3: Hypothesize

| What | Where |
|------|-------|
| Agent | `backend/agent_defs/hypothesizer.py` → `hypothesizer_agent` |
| Tool | `backend/tools/code_executor.py` → `execute_python()` |

The **Hypothesis Generator** agent takes EDA findings and forms a data-grounded hypothesis. It writes Python code to generate matplotlib/seaborn visualizations (saved as PNG), then presents a narrative citing specific data points with supporting charts.

---

## Core Requirements

| Requirement | Implementation |
|-------------|---------------|
| **Frontend** | Next.js 16 app in `frontend/` — chat interface with markdown answers, inline chart display, and an expandable `Agent Thinking` trace panel |
| **Agent Framework** | OpenAI Agents SDK (`openai-agents` package) — `Agent`, `function_tool`, `Runner.run()`, `handoffs` |
| **Tool Calling** | `query_database` (SQL), `run_analysis_code` (Python EDA), `create_visualization` (Python charts) |
| **Non-trivial Dataset** | NYC Airbnb data from Inside Airbnb: 13M+ calendar rows, 36K listings, 1M+ reviews |
| **Multi-agent Pattern** | Orchestrator-handoff: `orchestrator_agent` hands off sequentially to `collector_agent` → `analyst_agent` → `hypothesizer_agent` (see `backend/agent_defs/orchestrator.py`) |
| **Deployed** | GCP Cloud Run (Docker containers for backend + frontend) |
| **README** | This file |

---

## Grab-Bag Electives

### 1. Code Execution (2.5 pts)

| Where | `backend/tools/code_executor.py` → `execute_python()` |
|-------|-------------------------------------------------------|

The EDA Analyst and Hypothesis Generator agents write and execute arbitrary Python code at runtime. Code runs in a subprocess with access to pandas, numpy, scipy, matplotlib, seaborn, and duckdb. The executor captures stdout, stderr, exit code, and any saved artifacts (charts, CSVs).

### 2. Data Visualization (2.5 pts)

| Where | `backend/agent_defs/hypothesizer.py` → `create_visualization` tool |
|-------|---------------------------------------------------------------------|

The Hypothesis Generator writes matplotlib/seaborn code that saves charts as PNG files to an artifacts directory. These are served via FastAPI's `StaticFiles` mount at `/artifacts/` and displayed inline in the frontend chat interface.

### 3. Structured Output (bonus)

| Where | `backend/models/schemas.py` → `QueryResult`, `EDAFindings` |
|-------|-------------------------------------------------------------|

Pydantic models define structured schemas for query results and EDA findings, ensuring reliable data flow between agents.

### 4. Agent Thinking Trace

| Where | `frontend/src/components/ThinkingTrace.tsx` + `backend/main.py` |
|-------|----------------------------------------------------------------|

Each assistant answer can expose an expandable `Agent Thinking` panel beneath the response. When available, the backend returns a step-by-step trace of agent handoffs, tool calls, tool outputs, and intermediate messages. The frontend renders that trace as a collapsible timeline so you can inspect what happened under the hood for a given answer.

If a backend response does not include detailed trace data, the frontend falls back to a compact orchestration summary so the disclosure still explains how the answer was produced.

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Either an OpenAI API key or an OpenRouter API key

### Local Development

```bash
# 1. Clone and enter the project
cd airbnb

# 2. Backend setup
cd backend
cp .env.example .env
# Edit .env and add either OPENAI_API_KEY or OPENROUTER_API_KEY
# Optional: set AGENT_MODEL if you want to override the default model
# Defaults to gpt-4.1 (and uses the OpenAI-compatible provider path for OpenRouter)
pip install -r requirements.txt
python main.py
# Backend runs at http://localhost:8000

# 3. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
# Frontend runs at http://localhost:3000
```

### Docker

```bash
# Set one API key
export OPENAI_API_KEY=sk-...
# or
export OPENROUTER_API_KEY=sk-or-...

# Build and run
docker-compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

### GCP Cloud Run Deployment

```bash
# Build and push backend
cd backend
gcloud builds submit --tag gcr.io/PROJECT_ID/airbnb-backend
gcloud run deploy airbnb-backend \
  --image gcr.io/PROJECT_ID/airbnb-backend \
  --set-env-vars OPENAI_API_KEY=sk-... \
  --allow-unauthenticated

# Build and push frontend
cd ../frontend
gcloud builds submit --tag gcr.io/PROJECT_ID/airbnb-frontend
gcloud run deploy airbnb-frontend \
  --image gcr.io/PROJECT_ID/airbnb-frontend \
  --set-env-vars NEXT_PUBLIC_BACKEND_URL=https://airbnb-backend-xxx.run.app \
  --allow-unauthenticated
```

---

## Project Structure

```
airbnb/
├── backend/
│   ├── main.py                    # FastAPI app, HTTP + WebSocket endpoints
│   ├── agent_defs/
│   │   ├── orchestrator.py        # Orchestrator agent (handoff routing)
│   │   ├── collector.py           # Data Collector agent + query_database tool
│   │   ├── analyst.py             # EDA Analyst agent + run_analysis_code tool
│   │   └── hypothesizer.py        # Hypothesis agent + create_visualization tool
│   ├── tools/
│   │   ├── sql_runner.py          # DuckDB connection, view registration, SQL execution
│   │   └── code_executor.py       # Sandboxed Python execution with artifact capture
│   ├── models/
│   │   └── schemas.py             # Pydantic structured output models
│   ├── artifacts/                 # Generated charts and outputs (runtime)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx         # Root layout
│   │   │   ├── page.tsx           # Main chat page
│   │   │   └── globals.css        # Styles
│   │   └── components/
│   │       ├── Header.tsx         # App header
│   │       ├── ChatInput.tsx      # Input with suggested questions
│   │       ├── MessageBubble.tsx  # Message renderer (markdown, charts, trace toggle)
│   │       └── ThinkingTrace.tsx  # Expandable agent execution timeline
│   ├── next.config.ts
│   ├── Dockerfile
│   └── package.json
├── Sample Data/                   # NYC Airbnb data files
│   ├── calendar.csv.gz            # 13M+ rows of daily availability/pricing
│   ├── listings.csv               # 36K listings with 85 columns
│   ├── listings(1).csv            # Summary listing view
│   ├── reviews.csv                # 1M+ reviews
│   ├── neighbourhoods.csv         # Neighbourhood names
│   └── neighbourhoods.geojson     # Neighbourhood boundaries
├── docker-compose.yml
└── README.md
```

---

## Data Source

[Inside Airbnb](http://insideairbnb.com/) — New York City, scraped February 2026. The dataset is real, non-trivial (~100M+ data points across calendar, listings, and reviews), and cannot be trivially loaded into context.
