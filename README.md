# Researcher
 
Multi-agent AI research system that breaks a question into sub-questions, researches them in parallel, and streams back a synthesized report.
 
## How it works
 
Enter any question and a planner agent breaks it into focused sub-questions. Up to 12 research agents run in parallel, each using OpenAI function calling and Tavily search to gather sources. A synthesis agent then combines all results and streams a comprehensive markdown report back to the frontend over SSE. Results are cached for 24 hours and all sessions are persisted to Postgres.
 
## Architecture
 
- **Planner agent** — decomposes the question into N sub-questions via GPT-4o-mini
- **Research agents** — up to 12 parallel async agents using OpenAI function calling and Tavily search
- **Synthesis agent** — streams a markdown report from all research results over SSE
- **Caching** — Upstash Redis caches results for 24 hours
- **Evaluator** — an LLM-as-judge pass scores the finished report on five
  dimensions (relevance, accuracy, source coverage, coherence, completeness) and
  returns strengths, suggested improvements, and flags. Streamed to the client
  as an `evaluation` event.
- **Persistence** — Supabase PostgreSQL stores all sessions, including
  end-to-end `duration_ms` per run
 
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
# Unit tests (no API keys needed)
venv/bin/python -m pytest tests/test_cache.py tests/test_main.py -v

# Integration tests (require real API keys in .env)
venv/bin/python -m pytest tests/test_planner.py tests/test_orchestrator.py tests/test_evaluator.py -v
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

## Known limitations

- **The evaluator measures faithfulness, not accuracy.** Its "accuracy"
  dimension only checks whether the report is supported by the research inputs
  that were gathered — it never verifies those inputs against the world. A
  confidently wrong source that the report faithfully summarises scores well.
  The dimension is misnamed; renaming it is the next change.
- **One judge, and the scores are averaged.** A single OpenAI model evaluates,
  and `overall_score` is a weighted mean of the five dimensions. There is no
  second opinion and no way to see disagreement between evaluators.
- Prototype. Built to explore multi-agent orchestration, not to run in
  production.

## What I'd build next

- Rename the `accuracy` dimension to `faithfulness` so the metric matches what
  it measures.
- Put the judge behind a provider-independent interface with an OpenAI and a
  Claude implementation, keep both sets of scores separately, and surface
  disagreement rather than averaging it away.
- Source-level verification, so a claim can be checked against the source it
  cites rather than against the research bundle as a whole.
