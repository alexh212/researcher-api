import pytest
from agents.evaluator import evaluate_report

MOCK_QUESTION = "What are the main causes and effects of climate change?"

MOCK_RESULTS = [
    {
        "sub_question": "What are the primary causes of climate change?",
        "summary": "The primary causes of climate change include greenhouse gas emissions from burning fossil fuels, deforestation, and industrial processes. CO2 levels have risen from 280 ppm pre-industrial to over 420 ppm today. Source: https://climate.nasa.gov",
        "sources": ["https://climate.nasa.gov"],
    },
    {
        "sub_question": "What are the major effects of climate change?",
        "summary": "Major effects include rising global temperatures, sea level rise, increased frequency of extreme weather events, and biodiversity loss. The IPCC projects 1.5-4.5°C warming by 2100. Source: https://ipcc.ch",
        "sources": ["https://ipcc.ch"],
    },
]

MOCK_REPORT = """# Climate Change: Causes and Effects

## Executive Summary
Climate change is driven primarily by greenhouse gas emissions and has wide-ranging impacts on global systems.

## Causes
Burning fossil fuels and deforestation have pushed CO2 from 280 ppm to over 420 ppm ([NASA](https://climate.nasa.gov)).

## Effects
Rising temperatures, sea level rise, and extreme weather are among the key consequences ([IPCC](https://ipcc.ch)).

## Key Takeaways
- Human activity is the dominant cause
- Effects are already measurable and accelerating
"""


@pytest.mark.asyncio
async def test_evaluate_report_returns_valid_structure():
    evaluation = await evaluate_report(MOCK_QUESTION, MOCK_RESULTS, MOCK_REPORT)

    assert "scores" in evaluation
    assert "overall_score" in evaluation

    scores = evaluation["scores"]
    expected_dimensions = ["relevance", "accuracy", "source_coverage", "coherence", "completeness"]
    for dim in expected_dimensions:
        assert dim in scores
        assert isinstance(scores[dim], (int, float))
        assert 1 <= scores[dim] <= 5

    assert isinstance(evaluation["overall_score"], (int, float))
    assert 1 <= evaluation["overall_score"] <= 5


@pytest.mark.asyncio
async def test_evaluate_report_returns_qualitative_feedback():
    evaluation = await evaluate_report(MOCK_QUESTION, MOCK_RESULTS, MOCK_REPORT)

    assert "strengths" in evaluation
    assert "improvements" in evaluation
    assert isinstance(evaluation["strengths"], list)
    assert isinstance(evaluation["improvements"], list)


@pytest.mark.asyncio
async def test_evaluate_report_handles_failed_research():
    results_with_error = [
        {
            "sub_question": "What are the causes?",
            "summary": "Research failed: API timeout",
            "sources": [],
            "error": True,
        },
        MOCK_RESULTS[1],
    ]

    evaluation = await evaluate_report(MOCK_QUESTION, results_with_error, MOCK_REPORT)
    assert "scores" in evaluation
    assert "overall_score" in evaluation
