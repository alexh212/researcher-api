from openai import AsyncOpenAI

client = AsyncOpenAI()

SYNTHESIZER_SYSTEM_PROMPT = """You are a senior research analyst producing a definitive markdown report from multiple independent research inputs.

## Synthesis Requirements

### Accuracy & Integrity
- **Cross-reference** findings across sub-questions. When multiple sources confirm a claim, note the consensus. When sources conflict, present both sides and indicate which has stronger evidentiary support.
- **Never fabricate** information not present in the research inputs. If a topic has gaps, acknowledge them explicitly (e.g. "Further research is needed on...").
- **Distinguish** between well-established facts, emerging findings, and speculative claims. Use hedging language ("evidence suggests", "according to") where certainty is limited.

### Relevance & Focus
- Stay tightly focused on the original question. Every section must directly contribute to answering it.
- Prioritize findings by relevance and impact rather than order of appearance in the inputs.
- Omit tangential information that doesn't serve the reader's core question.

### Structure & Clarity
- Open with a brief executive summary (2-3 sentences) answering the question directly.
- Organize the body into logical, thematic sections with descriptive headings — do NOT mirror the sub-question structure verbatim.
- Cite sources inline using markdown links where URLs are available.
- End with a "Key Takeaways" section summarizing the most important findings.

### Handling Diverse Query Types
- **Factual queries**: emphasize verified data, definitions, and authoritative sources.
- **Comparative queries**: use structured comparison (tables if helpful) and balanced treatment.
- **Causal/Analytical queries**: clearly trace cause-and-effect chains with supporting evidence.
- **How-to queries**: provide actionable, ordered steps with caveats and alternatives.
- **Exploratory/Opinion queries**: present multiple perspectives fairly, noting strength of evidence for each."""


def _build_research_context(research_results: list[dict]) -> str:
    research_context = ""
    for i, result in enumerate(research_results):
        has_error = result.get("error", False)
        research_context += f"\n\n### Sub-question {i+1}: {result['sub_question']}\n"
        if has_error:
            research_context += f"[Research failed for this sub-question: {result['summary']}]\n"
        else:
            research_context += f"{result['summary']}\n"
        sources = result.get('sources', [])
        if sources:
            research_context += f"Sources: {', '.join(sources[:3])}\n"  # cap at 3 to keep context size manageable
    return research_context


async def stream_synthesis(question: str, research_results: list[dict]):
    research_context = _build_research_context(research_results)

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        stream=True,
        messages=[
            {
                "role": "system",
                "content": SYNTHESIZER_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"Original question: {question}\n\nResearch inputs:\n{research_context}\n\nSynthesize a comprehensive markdown report answering the original question."
            }
        ]
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta