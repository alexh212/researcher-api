import pytest
from agents.orchestrator import orchestrate_research

@pytest.mark.asyncio
async def test_orchestrate_returns_results():
    sub_questions = ["What is the Chicxulub crater?"]
    results = await orchestrate_research(sub_questions)
    assert len(results) == 1
    assert "summary" in results[0]
    assert "sources" in results[0]

@pytest.mark.asyncio
async def test_orchestrate_handles_multiple():
    sub_questions = [
        "What caused dinosaur extinction?",
        "What is the Chicxulub crater?"
    ]
    results = await orchestrate_research(sub_questions)
    assert len(results) == 2
    assert all("summary" in r for r in results)