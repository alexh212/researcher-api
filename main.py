from fastapi import FastAPI
from database import supabase
from search import search_web
from openai import AsyncOpenAI
from agents.planner import plan_research
from agents.researcher import research_sub_question
from dotenv import load_dotenv
from agents.synthesizer import synthesize_report, stream_synthesis
from agents.orchestrator import orchestrate_research
from contextlib import asynccontextmanager
from cache import get_cached, set_cached
from sse_starlette.sse import EventSourceResponse
import json

load_dotenv()

@asynccontextmanager
async def lifespan(app):
    yield

app = FastAPI(lifespan=lifespan)
client = AsyncOpenAI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/research/stream")
async def stream_research(question: str):
    async def event_generator():
        try:
            yield {"data": json.dumps({"type": "status", "message": "Planning research..."})}
            sub_questions = await plan_research(question)
            yield {"data": json.dumps({"type": "sub_questions", "data": sub_questions})}

            # Check cache
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
            async for chunk in stream_synthesis(question, results):
                yield {"data": json.dumps({"type": "report_chunk", "chunk": chunk})}

            yield {"data": json.dumps({"type": "done"})}
        except Exception as e:
            yield {"data": json.dumps({"type": "error", "message": str(e)})}

    return EventSourceResponse(event_generator())