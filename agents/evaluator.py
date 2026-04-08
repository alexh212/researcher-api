import json
from openai import AsyncOpenAI

client = AsyncOpenAI()

EVALUATOR_SYSTEM_PROMPT = """You are a research quality evaluator. Given an original question, the research inputs that were gathered, and the final synthesized report, evaluate the report on the following dimensions.

## Evaluation Criteria

Score each dimension from 1 (poor) to 5 (excellent):

### 1. Relevance
- Does the report directly address the original question?
- Is the content focused, or does it wander into tangential topics?
- Would a reader feel their question was answered?

### 2. Accuracy
- Are claims supported by the provided research inputs?
- Does the report avoid introducing information not present in the sources?
- Are facts, figures, and dates consistent with the research inputs?
- Are uncertainties and limitations properly acknowledged?

### 3. Source Coverage
- Does the report draw from all (non-failed) research inputs?
- Are sources cited inline?
- Is the coverage balanced, or does it over-rely on a single sub-question?

### 4. Coherence
- Is the report well-structured and logically organized?
- Do sections flow naturally from one to another?
- Is the writing clear and free of contradictions?

### 5. Completeness
- Does the report cover the key aspects of the question?
- Are important caveats or alternative perspectives included?
- Does it provide actionable insights or clear conclusions?

## Output Format

Return ONLY valid JSON with this exact structure:
{
  "scores": {
    "relevance": <1-5>,
    "accuracy": <1-5>,
    "source_coverage": <1-5>,
    "coherence": <1-5>,
    "completeness": <1-5>
  },
  "overall_score": <1-5 weighted average>,
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<suggestion 1>", "<suggestion 2>"],
  "flags": ["<any accuracy concern or factual issue spotted>"]
}

No preamble, no explanation, no markdown. Just the JSON object."""


async def evaluate_report(
    question: str,
    research_results: list[dict],
    report: str,
) -> dict:
    research_summary = ""
    for i, result in enumerate(research_results):
        has_error = result.get("error", False)
        research_summary += f"\n### Sub-question {i+1}: {result['sub_question']}\n"
        if has_error:
            research_summary += "[Research failed]\n"
        else:
            research_summary += f"{result['summary'][:500]}\n"
        sources = result.get("sources", [])
        if sources:
            research_summary += f"Sources: {', '.join(sources[:3])}\n"

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": EVALUATOR_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"Original question: {question}\n\n"
                    f"Research inputs:\n{research_summary}\n\n"
                    f"Final report:\n{report}\n\n"
                    "Evaluate the report."
                ),
            },
        ],
    )

    content = response.choices[0].message.content.strip()

    try:
        evaluation = json.loads(content)
    except json.JSONDecodeError:
        evaluation = {
            "scores": {
                "relevance": 0,
                "accuracy": 0,
                "source_coverage": 0,
                "coherence": 0,
                "completeness": 0,
            },
            "overall_score": 0,
            "strengths": [],
            "improvements": [],
            "flags": ["Evaluation failed: could not parse evaluator response"],
            "raw_response": content,
        }

    return evaluation
