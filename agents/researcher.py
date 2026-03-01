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

    # First call - model decides to use the tool
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    message = response.choices[0].message

    # If the model called the search tool
    if message.tool_calls:
        tool_call = message.tool_calls[0]
        query = json.loads(tool_call.function.arguments)["query"]
        
        # Execute the search
        search_results = await search_web(query)
        
        # Feed results back to the model
        messages.append(message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(search_results)
        })

        # Second call - model writes the summary
        final_response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        return {
            "sub_question": sub_question,
            "summary": final_response.choices[0].message.content,
            "sources": [r["url"] for r in search_results]
        }

    # If model didn't use the tool, return what it said anyway
    return {
        "sub_question": sub_question,
        "summary": message.content,
        "sources": []
    }