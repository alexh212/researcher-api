import json
from openai import AsyncOpenAI
from search import search_web
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI()

async def research_sub_question(sub_question: str) -> dict:
    tools = [
        {
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
    ]

    messages = [
        {
            "role": "system",
            "content": "You are a research agent. Use the search_web tool to find information, then write a concise 2-3 paragraph summary of what you found. Always cite your sources by including the URLs."
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