import asyncio
import os

from supabase import create_client

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
