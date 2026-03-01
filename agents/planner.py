import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI()

async def plan_research(question: str) -> list[str]:
    if not question.strip():
        raise ValueError("Question cannot be empty")
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are a research planner. Given a question, break it down into 3-4 focused sub-questions that can be researched independently and in parallel.
                
Return ONLY a JSON array of strings. No preamble, no explanation, no markdown. Just the array.

Example:
["What were the environmental conditions before the event?", "What evidence exists for the cause?", "What was the immediate impact?", "What were the long term consequences?"]"""
            },
            {
                "role": "user",
                "content": f"Break this question into 3-4 research sub-questions: {question}"
            }
        ]
    )
    
    content = response.choices[0].message.content.strip()
    
    try:
        sub_questions = json.loads(content)
        if not isinstance(sub_questions, list):
            raise ValueError("Response is not a list")
        return sub_questions
    except json.JSONDecodeError:
        raise ValueError(f"Planner returned invalid JSON: {content}")