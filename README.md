# Researcher
 
Multi-agent AI research system that breaks a question into sub-questions, researches them in parallel, and streams back a synthesized report.
 
## How it works
 
Enter any question and a planner agent breaks it into focused sub-questions. Up to 12 research agents run in parallel, each using OpenAI function calling and Tavily search to gather sources. A synthesis agent then combines all results and streams a comprehensive markdown report back to the frontend over SSE. Results are cached for 24 hours and all sessions are persisted to Postgres.
 
## Architecture
 
- **Planner agent** — decomposes the question into N sub-questions via GPT-4o-mini
- **Research agents** — up to 12 parallel async agents using OpenAI function calling and Tavily search
- **Synthesis agent** — streams a markdown report from all research results over SSE
- **Caching** — Upstash Redis caches results for 24 hours
- **Persistence** — Supabase PostgreSQL stores all sessions
 
## Tech stack
 
FastAPI, Python, OpenAI API, Tavily Search API, Supabase, PostgreSQL, Upstash Redis, Next.js, TypeScript, pytest, GitHub Actions, Render, Vercel
 
## Live demo
 
https://researcher-web-nine.vercel.app
 
## Run locally
 
```bash
git clone https://github.com/alexh212/researcher-api
cd researcher-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API keys
uvicorn main:app --reload
```
 
## Tests
 
```bash
pytest
```
 
## Environment variables
 
```
OPENAI_API_KEY=
TAVILY_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
```
