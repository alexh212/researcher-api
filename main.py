import json
import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from agents.evaluator import evaluate_report
from agents.orchestrator import orchestrate_research
from agents.planner import plan_research
from agents.synthesizer import stream_synthesis
from cache import get_cached, set_cached
from database import save_session

load_dotenv()

_REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "UPSTASH_REDIS_REST_URL",
    "UPSTASH_REDIS_REST_TOKEN",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]

missing = [v for v in _REQUIRED_ENV_VARS if not os.getenv(v)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://researcher-nol3rto9j-alexh212s-projects.vercel.app",
        "https://researcher-web-nine.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/research/stream")
async def stream_research(question: str, num_agents: int = 4):
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if not (2 <= num_agents <= 12):
        raise HTTPException(status_code=400, detail="num_agents must be between 2 and 12")

    async def event_generator():
        try:
            start = time.time()
            yield {"data": json.dumps({"type": "status", "status": "planning", "message": "Planning research..."})}
            sub_questions = await plan_research(question, num_agents)
            yield {"data": json.dumps({"type": "sub_questions", "data": sub_questions})}

            cached = get_cached(question)
            if cached:
                yield {"data": json.dumps({"type": "status", "status": "writing", "message": "Found cached results, writing report..."})}
                results = cached
            else:
                yield {"data": json.dumps({"type": "status", "status": "researching", "message": "Researching..."})}
                results = await orchestrate_research(sub_questions)
                set_cached(question, results)
                yield {"data": json.dumps({"type": "research_complete", "data": results})}

            yield {"data": json.dumps({"type": "status", "status": "writing", "message": "Writing report..."})}
            full_report = ""
            async for chunk in stream_synthesis(question, results):
                full_report += chunk
                yield {"data": json.dumps({"type": "report_chunk", "chunk": chunk})}

            yield {"data": json.dumps({"type": "status", "status": "evaluating", "message": "Evaluating report quality..."})}
            evaluation = await evaluate_report(question, results, full_report)
            yield {"data": json.dumps({"type": "evaluation", "data": evaluation})}

            duration_ms = int((time.time() - start) * 1000)
            await save_session(question, sub_questions, full_report, duration_ms)

            yield {"data": json.dumps({"type": "done"})}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)})}

    return EventSourceResponse(event_generator())