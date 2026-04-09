import asyncio

from agents.researcher import research_sub_question

async def orchestrate_research(sub_questions: list[str]) -> list[dict]:
    tasks = [research_sub_question(q) for q in sub_questions]
    # return_exceptions=True prevents one failing agent from cancelling all others.
    # Exceptions are returned as values and handled per-item below.
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            output.append({
                "sub_question": sub_questions[i],
                "summary": f"Research failed: {str(result)}",
                "sources": [],
                "error": True
            })
        else:
            output.append(result)

    return output