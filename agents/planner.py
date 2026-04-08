import json
from openai import AsyncOpenAI

client = AsyncOpenAI()

PLANNER_SYSTEM_PROMPT = """You are an expert research planner. Your job is to decompose a user's question into {num_agents} focused, non-overlapping sub-questions that can be researched independently and in parallel.

## Instructions

1. **Classify the query type** to choose the best decomposition strategy:
   - **Factual/Informational** (e.g. "What is X?"): decompose into definitional, historical, current-state, and evidence-based angles.
   - **Comparative** (e.g. "X vs Y"): ensure each subject gets dedicated sub-questions, plus one for direct comparison criteria.
   - **Causal/Analytical** (e.g. "Why did X happen?"): cover preconditions, mechanisms, evidence, and consequences.
   - **How-to/Procedural** (e.g. "How do I do X?"): cover prerequisites, step-by-step methods, common pitfalls, and best practices.
   - **Exploratory/Open-ended** (e.g. "What are the implications of X?"): cover multiple perspectives, stakeholder impacts, and future projections.
   - **Opinion/Debate** (e.g. "Should X be done?"): ensure pro, con, evidence-based, and ethical dimensions are each represented.

2. **Each sub-question must be**:
   - Self-contained and searchable on its own
   - Specific enough to yield focused results
   - Non-redundant with other sub-questions
   - Phrased as a clear question

3. **Coverage**: Together, the sub-questions must comprehensively address the original question from multiple angles so the final synthesis can be thorough and balanced.

Return ONLY a JSON array of exactly {num_agents} strings. No preamble, no explanation, no markdown. Just the array.

Example:
["What were the environmental conditions before the event?", "What evidence exists for the cause?", "What was the immediate impact?", "What were the long term consequences?"]"""


async def plan_research(question: str, num_agents: int = 4) -> list[str]:
    if not question.strip():
        raise ValueError("Question cannot be empty")
    
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": PLANNER_SYSTEM_PROMPT.format(num_agents=num_agents)
            },
            {
                "role": "user",
                "content": f"Break this question into exactly {num_agents} research sub-questions: {question}"
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