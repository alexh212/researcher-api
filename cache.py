import os
import json
from upstash_redis import Redis

redis = Redis(
    url=os.getenv("UPSTASH_REDIS_REST_URL"),
    token=os.getenv("UPSTASH_REDIS_REST_TOKEN")
)

CACHE_TTL = 60 * 60 * 24  # 24 hours

def make_cache_key(question: str) -> str:
    return f"research:{question.lower().strip()}"

def get_cached(question: str):
    key = make_cache_key(question)
    data = redis.get(key)
    if data:
        return json.loads(data)
    return None

def set_cached(question: str, results: list[dict]):
    key = make_cache_key(question)
    redis.set(key, json.dumps(results), ex=CACHE_TTL)