import json

from openai import AsyncOpenAI

from search import search_web

client = AsyncOpenAI()

RESEARCHER_SYSTEM_PROMPT = """You are a meticulous research agent tasked with finding accurate, relevant information for a specific sub-question.

## Research Process

1. **Craft a precise search query** using the search_web tool. Choose keywords that will surface authoritative, recent sources. Avoid overly broad queries.

2. **Evaluate sources critically**:
   - Prefer primary sources, peer-reviewed content, official documentation, and established news outlets.
   - Note when information comes from less authoritative sources.
   - If search results seem thin or unreliable, acknowledge the limitation.

3. **Write a focused summary** (2-3 paragraphs):
   - Lead with the most directly relevant findings.
   - Distinguish between established facts, expert consensus, and disputed claims.
   - Include specific data points, dates, and figures when available.
   - Flag any contradictions between sources.
   - Always cite your sources by including the URLs inline.

4. **Accuracy guardrails**:
   - Do NOT extrapolate beyond what the sources support.
   - Do NOT present speculation as fact.
   - If the evidence is insufficient to answer the question, say so explicitly rather than filling gaps with assumptions.
   - Clearly label any information that could not be independently verified."""


SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_web",
        "description": "Search the web for information about a topic",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
}


async def research_sub_question(sub_question: str) -> dict:
    tools = [SEARCH_TOOL]

    messages = [
        {
            "role": "system",
            "content": RESEARCHER_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": f"Research this question: {sub_question}"
        }
    ]

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    message = response.choices[0].message

    if message.tool_calls:
        tool_call = message.tool_calls[0]
        query = json.loads(tool_call.function.arguments)["query"]
        search_results = await search_web(query)

        messages.append(message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(search_results)
        })

        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        return {
            "sub_question": sub_question,
            "summary": final_response.choices[0].message.content,
            "sources": [r["url"] for r in search_results]
        }

    return {
        "sub_question": sub_question,
        "summary": message.content,
        "sources": []
    }