from fastapi import FastAPI
from database import supabase
from search import search_web
from openai import AsyncOpenAI
from agents.planner import plan_research
from agents.researcher import research_sub_question
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
client = AsyncOpenAI()

@app.get("/health")
def health():
    return {"status": "ok"}

from agents.planner import plan_research
from agents.orchestrator import orchestrate_research
import time

@app.post("/api/test-orchestrator")
async def test_orchestrator(body: dict):
    question = body["question"]
    
    start = time.time()
    sub_questions = await plan_research(question)
    results = await orchestrate_research(sub_questions)
    duration_ms = int((time.time() - start) * 1000)
    
    return {
        "question": question,
        "sub_questions": sub_questions,
        "results": results,
        "duration_ms": duration_ms
    }

from agents.synthesizer import synthesize_report

@app.post("/api/test-synthesizer")
async def test_synthesizer(body: dict):
    question = body["question"]
    sub_questions = await plan_research(question)
    results = await orchestrate_research(sub_questions)
    report = await synthesize_report(question, results)
    return {"report": report}