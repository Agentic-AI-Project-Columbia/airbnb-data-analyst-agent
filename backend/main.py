import os
import sys
import json
import asyncio

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

sys.path.insert(0, os.path.dirname(__file__))

from openai import AsyncOpenAI
from agents import set_default_openai_client, set_tracing_disabled

openrouter_key = os.environ.get("OPENROUTER_API_KEY")
openai_key = os.environ.get("OPENAI_API_KEY")

if openrouter_key:
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_key,
    )
    set_default_openai_client(client)
    set_tracing_disabled(True)
elif not openai_key:
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


@app.post("/api/analyze")
async def analyze(payload: dict):
    """HTTP endpoint: accepts {"question": "..."} and returns the full analysis."""
    question = payload.get("question", "")
    if not question:
        return JSONResponse(status_code=400, content={"error": "No question provided"})

    try:
        result = await Runner.run(orchestrator_agent, input=question)

        artifacts = []
        if os.path.exists(ARTIFACTS_DIR):
            for run_dir in os.listdir(ARTIFACTS_DIR):
                run_path = os.path.join(ARTIFACTS_DIR, run_dir)
                if os.path.isdir(run_path):
                    for f in os.listdir(run_path):
                        artifacts.append(f"/artifacts/{run_dir}/{f}")

        return {
            "answer": result.final_output,
            "artifacts": artifacts,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.websocket("/ws/analyze")
async def websocket_analyze(websocket: WebSocket):
    """WebSocket endpoint for streaming agent progress."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            question = message.get("question", "")

            if not question:
                await websocket.send_json({"type": "error", "content": "No question"})
                continue

            await websocket.send_json({
                "type": "status",
                "content": "Starting analysis pipeline...",
                "agent": "Orchestrator",
            })

            try:
                result = await Runner.run(orchestrator_agent, input=question)

                artifacts = []
                if os.path.exists(ARTIFACTS_DIR):
                    for run_dir in os.listdir(ARTIFACTS_DIR):
                        run_path = os.path.join(ARTIFACTS_DIR, run_dir)
                        if os.path.isdir(run_path):
                            for f in os.listdir(run_path):
                                artifacts.append(f"/artifacts/{run_dir}/{f}")

                await websocket.send_json({
                    "type": "result",
                    "content": result.final_output,
                    "artifacts": artifacts,
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
