from openai import AsyncOpenAI
import os

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def synthesize_report(question: str, research_results: list[dict]) -> str:
    research_context = ""
    for i, result in enumerate(research_results):
        research_context += f"\n\n### Sub-question {i+1}: {result['sub_question']}\n"
        research_context += f"{result['summary']}\n"
        sources = result.get('sources', [])
        if sources:
            research_context += f"Sources: {', '.join(sources[:3])}\n"

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a research analyst. Write a comprehensive, well-structured markdown report synthesizing the provided research. Include sections, cite sources inline, and end with a summary."
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nResearch:\n{research_context}\n\nWrite a full markdown report."
            }
        ]
    )

    return response.choices[0].message.content

async def stream_synthesis(question: str, research_results: list[dict]):
    research_context = ""
    for i, result in enumerate(research_results):
        research_context += f"\n\n### Sub-question {i+1}: {result['sub_question']}\n"
        research_context += f"{result['summary']}\n"
        sources = result.get('sources', [])
        if sources:
            research_context += f"Sources: {', '.join(sources[:3])}\n"

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        stream=True,
        messages=[
            {
                "role": "system",
                "content": "You are a research analyst. Write a comprehensive, well-structured markdown report synthesizing the provided research. Include sections, cite sources inline, and end with a summary."
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nResearch:\n{research_context}\n\nWrite a full markdown report."
            }
        ]
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta