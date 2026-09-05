import json
from openai import AsyncOpenAI

client = AsyncOpenAI()

# The model is asked for the five dimensions only; overall_score is computed
# here. Asking a judge for its own weighted average made the number unauditable
# — the weights lived nowhere in the repo, so whatever came back was passed
# through unvalidated. These weights are a judgement call, not a calibrated
# result: faithfulness leads because an unsupported report is the failure that
# matters most for a research tool, and the three structural dimensions are
# deliberately the cheapest to move.
DIMENSION_WEIGHTS = {
    "faithfulness": 0.30,
    "relevance": 0.25,
    "source_coverage": 0.15,
    "coherence": 0.15,
    "completeness": 0.15,
}

EVALUATOR_SYSTEM_PROMPT = """You are a research quality evaluator. Given an original question, the research inputs that were gathered, and the final synthesized report, evaluate the report on the following dimensions.

## Evaluation Criteria

Score each dimension from 1 (poor) to 5 (excellent):

### 1. Relevance
- Does the report directly address the original question?
- Is the content focused, or does it wander into tangential topics?
- Would a reader feel their question was answered?

### 2. Faithfulness
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
    "faithfulness": <1-5>,
    "source_coverage": <1-5>,
    "coherence": <1-5>,
    "completeness": <1-5>
  },
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<suggestion 1>", "<suggestion 2>"],
  "flags": ["<any accuracy concern or factual issue spotted>"]
}

No preamble, no explanation, no markdown. Just the JSON object."""


def _failed_evaluation(content: str, reason: str) -> dict:
    return {
        "scores": {dim: 0 for dim in DIMENSION_WEIGHTS},
        "overall_score": 0,
        "strengths": [],
        "improvements": [],
        "flags": ["Evaluation failed: could not parse evaluator response"],
        "evaluation_failed": True,
        "failure_reason": reason,
        "raw_response": content,
    }


def parse_evaluation(content: str) -> dict:
    """Turn a raw evaluator response into a scored dict. No network calls.

    Split out from evaluate_report so the degradation path is testable without
    an API key: previously the only way to reach the fallback was a live call
    that happened to return malformed JSON.
    """
    try:
        evaluation = json.loads(content)
    except json.JSONDecodeError:
        return _failed_evaluation(content, "response was not valid JSON")

    if not isinstance(evaluation, dict):
        return _failed_evaluation(content, "response was not a JSON object")

    scores = evaluation.get("scores")
    if not isinstance(scores, dict):
        return _failed_evaluation(content, "response had no scores object")

    # A missing or non-numeric dimension is a failure, not something to default
    # to zero: a partial score set silently produces a low overall_score that
    # looks like a bad report rather than a broken evaluator.
    for dim in DIMENSION_WEIGHTS:
        value = scores.get(dim)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return _failed_evaluation(content, f"missing or non-numeric dimension: {dim}")

    evaluation["overall_score"] = round(
        sum(scores[dim] * weight for dim, weight in DIMENSION_WEIGHTS.items()), 1
    )
    evaluation.setdefault("strengths", [])
    evaluation.setdefault("improvements", [])
    evaluation.setdefault("flags", [])
    return evaluation


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
        # Constrains the response to a JSON object, which removes the most
        # common failure the fallback below exists for: a markdown-fenced reply.
        # The fallback stays because this guarantees shape, not correctness.
        response_format={"type": "json_object"},
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

    return parse_evaluation(content)
