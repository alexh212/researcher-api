# Researcher API

Multi-agent AI research system that breaks questions into sub-questions, researches them in parallel, and synthesizes a comprehensive report.

## Architecture

- **Planner Agent** — breaks question into N sub-questions using GPT-4o-mini
- **Research Agents** — parallel async agents using OpenAI function calling + Tavily search
- **Synthesis Agent** — streams a markdown report from all research results
- **Caching** — Upstash Redis caches results for 24 hours
- **Persistence** — Supabase PostgreSQL stores all sessions

## Tech Stack

- FastAPI, Python, async/await
- OpenAI API (function calling, streaming)
- Tavily Search API
- Supabase + PostgreSQL
- Upstash Redis
- Pytest + GitHub Actions CI
- Deployed on Render

## Live Demo

Frontend: https://researcher-web-nine.vercel.app

## Running Locally
```bash
git clone https://github.com/alexh212/researcher-api
cd researcher-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your API keys
uvicorn main:app --reload
```

## Environment Variables
```
OPENAI_API_KEY=
TAVILY_API_KEY=
SUPABASE_URL=
SUPABASE_KEY=
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
```