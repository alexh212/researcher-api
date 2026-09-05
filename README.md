# researcher-api

A FastAPI service that decomposes a question into sub-questions, researches each one in parallel with GPT-4o-mini agents using Tavily web search, and streams a synthesized markdown report plus an LLM-judge score back over Server-Sent Events.

**Status:** prototype
**Live:** https://researcher-api-bpkt.onrender.com — root, `/docs`, and `/health` all return 200. Frontend: https://researcher-web-nine.vercel.app

## The problem

The hard part is holding a multi-stage, multi-agent pipeline together inside one long-lived HTTP response. A single request fans out to up to 12 concurrent OpenAI agents, each doing a two-turn function-calling exchange against a live web-search API, then funnels back into a streaming synthesis call and a judging pass — while the client needs incremental progress instead of five minutes of silence. That forces every stage to tolerate partial failure without killing the whole run, and it means being honest about what the judging pass can actually prove: its "accuracy" score only checks faithfulness to the retrieved research, never truth.

## How it works

Everything is one endpoint: `GET /api/research/stream?question=...&num_agents=...` in `main.py:70`. It validates at the boundary first — empty question or `num_agents` outside 2–12 returns `HTTPException(400)` before any stream opens — then returns an `EventSourceResponse` emitting JSON-encoded SSE events in order:

1. `status: planning` → `plan_research` (`agents/planner.py:32`) makes one `gpt-4o-mini` call that classifies the query type and returns a bare JSON array of exactly `num_agents` sub-questions. A wrong count or non-list raises `ValueError`. Emitted as `sub_questions`.
2. `get_cached` (`cache.py:18`) checks Upstash Redis under `research:{question.lower().strip()}`, 24h TTL.
3. On a miss: `status: researching` → `orchestrate_research` (`agents/orchestrator.py:5`) runs `asyncio.gather(..., return_exceptions=True)` over `research_sub_question` (`agents/researcher.py:53`). Each agent does one OpenAI function call, executes `search_web` (`search.py:8`, POSTs to `api.tavily.com/search`, `max_results: 5`, `search_depth: "basic"`), and writes a summary from the results. A dead agent becomes an `{"error": True}` placeholder instead of killing the batch. Cached and emitted as `research_complete`.
4. `status: writing` → `stream_synthesis` (`agents/synthesizer.py:48`) concatenates the summaries (failed sub-questions marked inline, sources capped at three each) and streams one `gpt-4o-mini` completion, forwarding each delta as a `report_chunk` event.
5. `status: evaluating` → `evaluate_report` (`agents/evaluator.py:58`) rebuilds the research summary truncated to 500 chars per entry and scores relevance, accuracy, source_coverage, coherence, and completeness 1–5, plus an overall score. A JSON parse failure falls back to an all-zero score with `flags: ["Evaluation failed..."]`. Emitted as `evaluation`.
6. `save_session` (`database.py:12`) inserts the question, sub-questions, report, and duration into Supabase, off-thread, wrapped in a bare `except: pass`.
7. `done`. Any exception in the generator is caught and re-emitted as an `error` event with the raw exception string.

`main.py:10` loads `.env` before the local imports because `cache.py`, `database.py`, and `search.py` all read credentials at module scope; `main.py:32` hard-fails with `RuntimeError` at import time if any required var is missing. CORS is a hardcoded three-origin allowlist (`main.py:40`).

## Setup

```bash
git clone https://github.com/alexh212/researcher-api
cd researcher-api
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# fill in all six values below — main.py raises RuntimeError at import time
# if any one is empty, so uvicorn won't boot on a partial file
uvicorn main:app --reload
# verify: curl http://127.0.0.1:8000/health -> {"status":"ok"}
# docs at http://127.0.0.1:8000/docs
```

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Powers every LLM call — planning, research, synthesis, evaluation (all `gpt-4o-mini`). |
| `TAVILY_API_KEY` | The only web-search path (`search.py`); without it every research agent fails. |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST client for the 24h result cache. |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase client used to insert rows into the `sessions` table. |

## Tests

```bash
pytest tests/test_cache.py tests/test_main.py -v   # 10 tests, no API keys needed
pytest tests/ -v                                    # full suite — makes live, billed OpenAI + Tavily calls
```

CI runs the full suite on every push, including the three integration tests, so a push spends real credits and any provider outage turns the build red. The CI test step also has a dead fallback (`venv/bin/pytest ... || pytest ...`) — the first half can never succeed because the workflow never creates a venv.

## Known limitations

- **The evaluator measures faithfulness, not accuracy.** Its "accuracy" dimension only checks whether the report is supported by the research it was given — never whether that research is true. A confidently wrong source the report faithfully summarizes still scores well. Worse, the judge sees a truncated copy of the inputs: each research summary is cut to 500 characters and capped at three sources, so even the faithfulness check runs against a partial view of what the researchers actually found.
- **`overall_score` isn't computed by any code.** The prompt asks the model for "a 1–5 weighted average" but no weights are defined anywhere in the repo — whatever number the model returns is passed through unvalidated.
- **The cache is wrong twice over.** The cache key ignores `num_agents`, so a 12-agent request can be served research cached under a 4-agent run for the same question text. And the planner runs before the cache is checked, so every cache hit still burns a planner LLM call and shows the client sub-questions that don't match the cached research. On top of that, a cache hit never emits `research_complete` at all — that event only fires in the miss branch — so the frontend's agent cards stay empty on a hit despite a commit titled "complete agent cards on cache hit."
- **One search per agent, no retry, no timeout.** Each research agent takes only `tool_calls[0]`; any further tool calls the model makes are silently dropped, and there's no second round of searching after it sees results. Five Tavily results at `search_depth: "basic"` is the entire evidence base per sub-question. Nothing in the app sets a timeout — not the `httpx.AsyncClient`, not any of the four OpenAI clients — so a slow upstream can stall the stream indefinitely. `tenacity` is in `requirements.txt` but never imported.
- **Session persistence is dead, and the code can't tell.** The Supabase project
  the app writes to no longer resolves — `NXDOMAIN` on the host in `SUPABASE_URL`.
  Free projects are paused after a week idle and deleted at 90 days. Because
  `database.py:22` wraps the insert in a bare `except Exception: pass` with no
  logging, every run since has failed to persist without producing any signal.
  Nothing reads the `sessions` table back either, so there was no second way to
  notice. The swallowed exception is the actual bug; the dead project is just
  what it hid.
- **Neither JSON-producing prompt is hardened.** The planner does a bare `json.loads`; a markdown-fenced response raises and kills the whole run as an SSE error. The evaluator degrades instead of crashing, but its own fallback returns 0 for every dimension, and `tests/test_evaluator.py` asserts `1 <= scores[dim] <= 5` — meaning the documented degradation path is actually a test failure, not a covered case. Neither prompt uses `response_format={"type": "json_object"}`.
- **The endpoint is public and unmetered.** No API key, no rate limit, no per-IP quota — any caller can spend OpenAI and Tavily credits on demand. The CORS allowlist doesn't help here; it constrains browsers, not curl, and one of its three entries is a stale Vercel preview URL.
- **requirements.txt is a raw `pip freeze`,** not a dependency list — it includes packages like pyiceberg, cryptography, and rich that nothing in the project imports. There's no pyproject.toml and no deployment config in the repo at all (no Dockerfile, no render.yaml); the live Render service is configured entirely outside the codebase.
- An unmerged `origin/v2` branch has auth, an access chokepoint, and a schema migration for projects/reports/runs/sharing. None of it is on `main`.

## What I'd build next

- Rename the evaluator's `accuracy` dimension to `faithfulness` so the metric's name matches what it measures.
- Put the judge behind a provider-independent interface with OpenAI and Claude implementations, keep both score sets separate, and surface disagreement instead of averaging it away — and compute `overall_score` in Python from explicit weights instead of asking the model for it.
- Fix the cache: include `num_agents` in the key, check the cache before running the planner, store sub-questions alongside results, and emit `research_complete` on a hit.
- Log the Supabase failure instead of swallowing it, then either re-provision the
  project or drop the dependency. Right now the code carries a persistence layer
  that does nothing.
- Gate the endpoint before anything else — an API key or per-IP rate limit on `/api/research/stream`, plus explicit `httpx` and OpenAI timeouts, so an unauthenticated caller can't run up the bill or hold a stream open forever.
