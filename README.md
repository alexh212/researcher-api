# Scout API

Scout breaks a question into smaller research tasks, runs them concurrently, and streams a report to a web interface. This repository contains the FastAPI backend. It uses OpenAI for planning, research, synthesis, and evaluation, with Tavily available as a search tool.

**Status: prototype.** The public endpoint uses paid services and has no application authentication or usage quotas. Use non-sensitive questions for testing.

[Demo](https://researcher-web-nine.vercel.app/) · [API docs](https://researcher-api-bpkt.onrender.com/docs) · [Frontend source](https://github.com/alexh212/researcher-web)

The backend is hosted at [researcher-api-bpkt.onrender.com](https://researcher-api-bpkt.onrender.com/). Its root and `/health` routes identify the service and confirm that it can respond; they do not check external dependencies.

## Request flow

`GET /api/research/stream?question=...&num_agents=...` accepts a nonempty question and between 2 and 12 agents. The default is 4. Progress and results are sent as Server-Sent Events (SSE).

1. **Plan.** A planner asks `gpt-4o-mini` to split the question into the requested number of sub-questions.
2. **Check the cache.** Upstash Redis stores researcher results for 24 hours. The key includes the normalized question and agent count: `research:{question.lower().strip()}:{num_agents}`.
3. **Research on a cache miss.** `asyncio.gather(..., return_exceptions=True)` runs the researchers concurrently. Each can request a Tavily search through function calling. Search is optional; an agent can return a response without sources. Failed researchers become error entries, and the batch is cached.
4. **Write and evaluate.** The synthesizer streams the report text. A separate model call evaluates the completed report and returns one structured result. Cached research still gets a fresh report and evaluation.
5. **Save the session.** The backend attempts to store the question, sub-questions, report, and duration in Supabase. Insert failures are caught and logged without preventing normal stream completion.

The SSE event types are `status`, `sub_questions`, `research_complete`, `report_chunk`, `evaluation`, `done`, and `error`. Other exceptions in the stream generator end the run with an `error` event containing the exception message. The cache-hit path skips `research_complete` and moves to `writing`.

The route is in [main.py](main.py); the individual stages are in [agents/](agents/). [cache.py](cache.py) handles Redis and [database.py](database.py) handles session storage.

## Evaluation

The judge uses `gpt-4o-mini`, the same model used to write the report. It receives the question, finished report, and research context limited to 500 characters and three source URLs per researcher. It does not open those URLs.

| Dimension | Weight |
| --- | --- |
| Faithfulness to the supplied research | 30% |
| Relevance | 25% |
| Source coverage | 15% |
| Coherence | 15% |
| Completeness | 15% |

The evaluator requests JSON object mode and validates the response in Python. The model supplies the individual scores. Python calculates the weighted average and rounds it to one decimal place. These weights have not been calibrated against human ratings.

[parse_evaluation](agents/evaluator.py) checks for a JSON object containing all five numeric scores, excluding booleans. Invalid responses return `evaluation_failed: true` with a reason and zero placeholders. Those zeros indicate an unusable evaluation, not a low-quality report. Score range and finite-number checks are not implemented.

Faithfulness measures agreement with the supplied research, not independent factual accuracy. The report has already streamed before evaluation begins; the judge does not approve publication or trigger a rewrite. Provider failures follow the route's error path rather than the parser fallback.

## Run locally

```bash
git clone https://github.com/alexh212/researcher-api.git
cd researcher-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in all six environment variables before starting the server.
uvicorn main:app --reload
```

| Variable | Used for |
| --- | --- |
| `OPENAI_API_KEY` | Planning, research, synthesis, and evaluation |
| `TAVILY_API_KEY` | Requested web searches |
| `UPSTASH_REDIS_REST_URL` | Research cache connection |
| `UPSTASH_REDIS_REST_TOKEN` | Research cache credentials |
| `SUPABASE_URL` | Session database connection |
| `SUPABASE_KEY` | Session database credentials |

`load_dotenv()` runs before local imports because several modules create clients at import time. Startup requires all six values, including Supabase settings even when session persistence is not being used successfully.

Open `http://localhost:8000/docs` for the API schema. The CORS allowlist is defined in `main.py`; additional frontend origins require configuration changes.

## Tests

For the cache-key and parser tests, which make no provider requests:

```bash
pytest tests/test_cache.py tests/test_evaluator_parse.py -v
```

**The following commands can make paid requests and write to configured services:**

```bash
pytest tests/test_cache.py tests/test_main.py tests/test_evaluator_parse.py -v
pytest tests/ -v
```

The route boundary test submits valid research requests. Fixtures supply dummy credentials only when variables are absent, so existing credentials remain active. The full suite also includes live provider tests.

CI runs the full suite on pushes to `main` and pull requests targeting it, including documentation-only changes. With configured secrets, CI can spend OpenAI/Tavily credits and attempt cache and session writes. Passing parser tests verifies handling and arithmetic, not the model's judgment quality.

## Current limitations

- **Cache consistency:** planning happens before lookup. A new plan can differ from the plan that produced cached research, because the cache stores research results without the original plan. Failed researcher entries can also be cached.
- **Research scope:** each researcher executes at most the first requested tool call, with up to five basic Tavily results. It cannot search again after reading those results. SDK defaults provide some timeout/retry behavior, but there is no application-level run deadline or researcher retry policy.
- **Planner parsing:** malformed JSON can end the whole run. The planner does not yet have the evaluator's tested parsing fallback.
- **Persistence:** the locally configured Supabase hostname failed DNS resolution during the September 7 review. Successful deployed saves and historical records remain unverified. The app has no session-history reader.
- **Public access:** there is no application authentication, rate limit, or per-user quota. CORS is not an access-control or spending limit. Error events can expose raw exception details.
- **Deployment and dependencies:** Render configuration is maintained outside this repository. `requirements.txt` includes unused packages and needs a dependency cleanup. The separate `v2` branch is not part of `main`.

Next priorities are access and spending controls, more reliable planner parsing, storing plans with cached research, and deciding whether to restore or remove session persistence. Evaluation needs human-reviewed examples before its scores can be treated as a reliable quality measure; comparing independent judges is another possible follow-up.
