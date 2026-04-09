import os

# Set fake env vars before any module is imported.
# AsyncOpenAI() and other clients read from os.environ at instantiation time,
# so this must run at conftest import time (before collection), not in fixtures.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("TAVILY_API_KEY", "test-key")
os.environ.setdefault("UPSTASH_REDIS_REST_URL", "https://fake.upstash.io")
os.environ.setdefault("UPSTASH_REDIS_REST_TOKEN", "test-token")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
