import asyncio
import logging
import os

from supabase import create_client

logger = logging.getLogger(__name__)

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
        # Still caught: persistence is not part of the research result, so a
        # failed insert must not kill an in-flight SSE stream. But it is logged
        # now — the bare `pass` let this dependency die silently for months.
        logger.exception("Failed to insert research session into Supabase")
