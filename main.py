from fastapi import FastAPI
from database import supabase
from search import search_web
from openai import AsyncOpenAI
from agents.planner import plan_research
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
client = AsyncOpenAI()

@app.get("/health")
def health():
    return {"status": "ok"}