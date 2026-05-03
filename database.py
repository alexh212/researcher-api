import asyncio
import os

from supabase import create_client
from access import UserContext

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


async def save_session(question: str, sub_questions: list, report: str, duration_ms: int):
    data = {
        "question": question,
        "sub_questions": sub_questions,
        "report": report,
        "duration_ms": duration_ms
    }
    try:
        await asyncio.to_thread(
            lambda: supabase.table("sessions").insert(data).execute()
        )
    except Exception:
        pass


async def upsert_user(user: UserContext):
    data = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
    }
    await asyncio.to_thread(
        lambda: supabase.table("users").upsert(data, on_conflict="id").execute()
    )
