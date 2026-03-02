from fastapi import FastAPI
from agents.planner import plan_research
from agents.synthesizer import stream_synthesis
from agents.orchestrator import orchestrate_research
from contextlib import asynccontextmanager
from cache import get_cached, set_cached
from sse_starlette.sse import EventSourceResponse
from database import save_session
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import json
import time

load_dotenv()

@asynccontextmanager
async def lifespan(app):
    yield

app = FastAPI(lifespan=lifespan)

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
    async def event_generator():
        try:
            start = time.time()
            yield {"data": json.dumps({"type": "status", "message": "Planning research..."})}
            sub_questions = await plan_research(question, num_agents)
            yield {"data": json.dumps({"type": "sub_questions", "data": sub_questions})}

            cached = get_cached(question)
            if cached:
                yield {"data": json.dumps({"type": "status", "message": "Found cached research, writing report..."})}
                results = cached
            else:
                yield {"data": json.dumps({"type": "status", "message": "Researching..."})}
                results = await orchestrate_research(sub_questions)
                set_cached(question, results)
                yield {"data": json.dumps({"type": "research_complete", "data": results})}

            yield {"data": json.dumps({"type": "status", "message": "Writing report..."})}
            full_report = ""
            async for chunk in stream_synthesis(question, results):
                full_report += chunk
                yield {"data": json.dumps({"type": "report_chunk", "chunk": chunk})}

            duration_ms = int((time.time() - start) * 1000)
            await save_session(question, sub_questions, full_report, duration_ms)

            yield {"data": json.dumps({"type": "done"})}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)})}

    return EventSourceResponse(event_generator())