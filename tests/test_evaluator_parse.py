import json

from agents.evaluator import DIMENSION_WEIGHTS, parse_evaluation

# 5*0.30 + 4*0.25 + 3*0.15 + 2*0.15 + 1*0.15 = 3.4
# Deliberately five distinct scores: any other weighting produces a different
# number, so this asserts the weights themselves, not just that a float appears.
VALID = {
    "scores": {
        "faithfulness": 5,
        "relevance": 4,
        "source_coverage": 3,
        "coherence": 2,
        "completeness": 1,
    },
    "strengths": ["clear structure"],
    "improvements": ["cite more sources"],
    "flags": [],
}


def test_weights_sum_to_one():
    assert round(sum(DIMENSION_WEIGHTS.values()), 6) == 1.0


def test_valid_json_computes_weighted_overall_score():
    result = parse_evaluation(json.dumps(VALID))

    assert result["overall_score"] == 3.4
    assert result["scores"]["faithfulness"] == 5
    assert result["strengths"] == ["clear structure"]
    assert result["improvements"] == ["cite more sources"]
    assert "evaluation_failed" not in result


def test_markdown_fenced_json_falls_back():
    # response_format=json_object should prevent this, but the parser must not
    # depend on that holding. No fence stripper — a fenced response is a failure.
    fenced = "```json\n" + json.dumps(VALID) + "\n```"
    result = parse_evaluation(fenced)

    assert result["evaluation_failed"] is True
    assert result["overall_score"] == 0
    assert all(v == 0 for v in result["scores"].values())
    assert result["strengths"] == []
    assert result["improvements"] == []


def test_missing_dimension_falls_back():
    partial = json.loads(json.dumps(VALID))
    del partial["scores"]["coherence"]
    result = parse_evaluation(json.dumps(partial))

    assert result["evaluation_failed"] is True
    assert result["overall_score"] == 0
    assert set(result["scores"]) == set(DIMENSION_WEIGHTS)
