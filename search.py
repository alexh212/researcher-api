import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

async def search_web(query: str) -> list:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": 5,
                "search_depth": "basic"
            }
        )
        data = response.json()
        return [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content")
            }
            for r in data.get("results", [])
        ]