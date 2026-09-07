# researcher-api

A FastAPI service that decomposes a question into sub-questions, researches each one in parallel with GPT-4o-mini agents using Tavily web search, and streams a synthesized markdown report plus an LLM-judge score back over Server-Sent Events.

**Status:** prototype
**Live:** https://researcher-api-bpkt.onrender.com — root, `/docs`, and `/health` all return 200. Frontend: https://researcher-web-nine.vercel.app

## The problem

The hard part is holding a multi-stage, multi-agent pipeline together inside one long-lived HTTP response. A single request fans out to up to 12 concurrent OpenAI agents, each able to request a web search through a two-turn function-calling exchange, then funnels back into a streaming synthesis call and a judging pass — while the client needs incremental progress instead of five minutes of silence. That forces every stage to tolerate partial failure without killing the whole run, and it means being honest about what the judging pass can actually prove: its `faithfulness` score only checks whether the report matches the retrieved research, never whether that research is true.

## How it works

Everything is one endpoint: `GET /api/research/stream?question=...&num_agents=...` in `main.py:70`. It validates at the boundary first — empty question or `num_agents` outside 2–12 returns `HTTPException(400)` before any stream opens — then returns an `EventSourceResponse` emitting JSON-encoded SSE events in order:

1. `status: planning` → `plan_research` (`agents/planner.py:32`) makes one `gpt-4o-mini` call that classifies the query type and returns a bare JSON array of exactly `num_agents` sub-questions. A wrong count or non-list raises `ValueError`. Emitted as `sub_questions`.
2. `get_cached` (`cache.py:21`) checks Upstash Redis under `research:{question.lower().strip()}:{num_agents}`, 24h TTL. `num_agents` is in the key because the planner splits the question into exactly that many sub-questions, so the same question at 4 and at 12 agents is genuinely different research.
3. On a miss: `status: researching` → `orchestrate_research` (`agents/orchestrator.py:5`) runs `asyncio.gather(..., return_exceptions=True)` over `research_sub_question` (`agents/researcher.py:53`). Each agent calls OpenAI with `tool_choice="auto"`. If the model requests a tool, the agent executes the first tool call using `search_web` (`search.py:8`, POSTs to `api.tavily.com/search`, `max_results: 5`, `search_depth: "basic"`) and makes a second model call to summarize the results. Otherwise it returns the model response with an empty source list; web search is not guaranteed. A dead agent becomes an `{"error": True}` placeholder instead of killing the batch. Cached and emitted as `research_complete`.
4. `status: writing` → `stream_synthesis` (`agents/synthesizer.py:48`) concatenates the summaries (failed sub-questions marked inline, sources capped at three each) and streams one `gpt-4o-mini` completion, forwarding each delta as a `report_chunk` event.
5. `status: evaluating` → `evaluate_report` (`agents/evaluator.py:121`) rebuilds the research summary truncated to 500 chars per entry and asks for `faithfulness`, `relevance`, `source_coverage`, `coherence`, and `completeness` 1–5, under `response_format={"type": "json_object"}`. `overall_score` is not requested from the model: `parse_evaluation` (`agents/evaluator.py:85`) computes it in Python from `DIMENSION_WEIGHTS` (`agents/evaluator.py:13`) — faithfulness 0.30, relevance 0.25, source_coverage/coherence/completeness 0.15 each — rounded to one decimal. Invalid JSON or any missing/non-numeric dimension returns an all-zero fallback carrying `evaluation_failed: True`. Emitted as `evaluation`.
6. `save_session` (`database.py:15`) attempts to insert the question, sub-questions, report, and duration into Supabase, off-thread. The insert is still wrapped in `except Exception` — a failed write must not kill an in-flight stream — but `database.py:30` now logs it with `logger.exception` instead of discarding it.
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
| `TAVILY_API_KEY` | Powers the web-search path (`search.py`). A failed search becomes a failed researcher entry; an agent that does not request search can still return a response. |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis REST client for the 24h result cache. |
| `SUPABASE_URL` / `SUPABASE_KEY` | Supabase client used to insert rows into the `sessions` table. |

## Tests

```bash
pytest tests/test_cache.py tests/test_evaluator_parse.py -v  # 9 pure cache-key/parser tests; no network calls
pytest tests/test_cache.py tests/test_main.py tests/test_evaluator_parse.py -v  # 15 tests; boundary test enters the live pipeline
pytest tests/ -v                                    # full suite — makes live, billed OpenAI + Tavily calls
```

The nine-test command checks local calculations and parsing without making provider calls. The 15-test command also includes `test_num_agents_boundary_values_are_valid`, which submits two valid research requests. `tests/conftest.py` supplies dummy credentials only when variables are absent; it preserves existing credentials, so this command can spend credits and attempt cache/session writes in a configured environment.

CI runs the full suite on pushes to `main` and pull requests targeting `main`, including README-only changes. Planner, orchestrator, evaluator and valid-route tests invoke providers with configured secrets, so CI can spend OpenAI/Tavily credits and provider failures can fail the build. The CI test step also has a dead fallback (`venv/bin/pytest ... || pytest ...`) — the first half can never succeed because the workflow never creates a venv.

## Known limitations

- **Faithfulness is not accuracy, and the judge only sees part of the inputs.** The dimension is named for what it can actually check — whether the report is supported by the research it was given — but that means a confidently wrong source the report faithfully summarizes still scores well. Nothing here verifies truth. And the judge reads a truncated copy of the inputs: each research summary is cut to 500 characters and capped at three sources, so even the faithfulness check runs against a partial view of what the researchers found.
- **The weights are a judgement call, not a calibrated result.** `DIMENSION_WEIGHTS` is now explicit and applied in Python, which makes the number auditable and reproducible — but nobody validated 0.30/0.25/0.15/0.15/0.15 against human ratings. It encodes an opinion about what matters, not a measurement.
- **One judge, same model family.** `gpt-4o-mini` grades a report written by `gpt-4o-mini`. There is no second opinion and no human-rated baseline, so a systematic blind spot shared by writer and judge is invisible to this pipeline by construction.
- **Cache hits still run the planner.** A hit spends a planner LLM call and may show newly generated sub-questions that differ from the cached research. The cache stores researcher results, not the plan. The hit branch does not emit `research_complete`, but the frontend completes its agent cards on `status: writing`, so the cards do not stay empty because of the missing event.
- **Search is limited and timeout/retry policies use SDK defaults.** An agent executes at most the first requested tool call, with up to five Tavily results at `search_depth: "basic"`, and cannot search again after seeing those results. It may also return without requesting search. The app does not configure its own request timeouts or retry policy: the pinned OpenAI SDK defaults to a 600-second timeout (5-second connect timeout) and two retries for eligible failures; HTTPX defaults to 5-second network-operation timeouts. These are not an overall research-run deadline. The orchestrator does not rerun failed researchers. `tenacity` is listed but not imported by the app.
- **Deployed session persistence is unresolved.** During the September 7 verification, the Supabase hostname in the local configuration did not resolve. The deployed configuration, database contents and historical writes were not inspected, so this does not establish when persistence failed or whether the project was deleted. `database.py` attempts an insert and catches failures with `logger.exception`, including the traceback. Logging exposes a failed write; it does not repair persistence. Nothing in the app reads sessions back.
- **The planner's JSON handling is still unhardened.** It does a bare `json.loads` with no `response_format`, so a markdown-fenced response raises and kills the whole run as an SSE error. The evaluator no longer has this problem — it requests `json_object` and degrades through `parse_evaluation`, whose fallback is covered by `tests/test_evaluator_parse.py` without an API key — but the planner never got the same treatment, and it fails harder, because it runs first and takes the stream down with it.
- **The endpoint is public and unmetered.** No API key, no rate limit, no per-IP quota — any caller can spend OpenAI and Tavily credits on demand. The CORS allowlist doesn't help here; it constrains browsers, not curl, and one of its three entries is a stale Vercel preview URL.
- **requirements.txt is a raw `pip freeze`,** not a dependency list — it includes packages like pyiceberg, cryptography, and rich that nothing in the project imports. There's no pyproject.toml and no deployment config in the repo at all (no Dockerfile, no render.yaml); the live Render service is configured entirely outside the codebase.
- An unmerged `origin/v2` branch has auth, an access chokepoint, and a schema migration for projects/reports/runs/sharing. None of it is on `main`.

## What I'd build next

- Give the planner the same treatment the evaluator just got: `response_format={"type": "json_object"}` and a tested pure parser, so a malformed plan degrades instead of killing the stream.
- Put the judge behind a provider-independent interface with OpenAI and Claude implementations, keep both score sets separate, and surface disagreement instead of averaging it away. Two judges that disagree is information; a mean hides it.
- Fix the rest of the cache: check it before running the planner, store sub-questions alongside results, and emit `research_complete` on a hit.
- Verify the deployed Supabase configuration and whether session history is needed. Restore persistence if required, or remove the dependency deliberately; the current logging change alone does not establish successful saves.
- Gate the endpoint before anything else — an API key or per-IP rate limit on `/api/research/stream`, plus explicit request timeouts and an overall run budget, so usage and waiting time are bounded beyond SDK defaults.
