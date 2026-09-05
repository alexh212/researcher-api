import json
import os

from upstash_redis import Redis

redis = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
)

CACHE_TTL = 60 * 60 * 24  # 24 hours


def make_cache_key(question: str, num_agents: int) -> str:
    # num_agents is part of the key because it changes the research itself: the
    # planner splits the question into exactly that many sub-questions, so a
    # 4-agent run and a 12-agent run produce different results for one question.
    return f"research:{question.lower().strip()}:{num_agents}"


def get_cached(question: str, num_agents: int):
    key = make_cache_key(question, num_agents)
    try:
        data = redis.get(key)
        if data:
            return json.loads(data)
    except Exception:
        pass  # Cache is best-effort — a Redis failure should not break a research request
    return None


def set_cached(question: str, num_agents: int, results: list[dict]):
    key = make_cache_key(question, num_agents)
    try:
        redis.set(key, json.dumps(results), ex=CACHE_TTL)
    except Exception:
        pass  # Same — write failures are acceptable, the request still completes
