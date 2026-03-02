import pytest
from agents.planner import plan_research

@pytest.mark.asyncio
async def test_plan_research_returns_list():
    result = await plan_research("what caused the extinction of dinosaurs", num_agents=3)
    assert isinstance(result, list)
    assert len(result) == 3
    assert all(isinstance(q, str) for q in result)

@pytest.mark.asyncio
async def test_plan_research_empty_question():
    with pytest.raises(ValueError):
        await plan_research("", num_agents=3)