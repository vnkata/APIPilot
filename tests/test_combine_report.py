import json

from api_testing.constraint.combine_report import generate_combination_report


def test_generate_combination_html_report_contains_filters_and_evidence(tmp_path):
    source = tmp_path / "combine_constraint_miners.json"
    source.write_text(
        json.dumps(
            {
                "get-/things": {
                    "return.count": {
                        "endpoint": "get-/things",
                        "property": "return.count",
                        "static_constraint": "gte(return.count, 0)",
                        "dynamic_constraint": "eq(return.count, 5)",
                        "status": "NOT_COMBINED",
                        "verdict": "STATIC_WIN",
                        "final_constraint": "gte(return.count, 0)",
                        "reason": "Runtime selected the static rule.",
                        "runtime_evaluation": {
                            "static_expression": "gte(return.count, 0)",
                            "dynamic_expression": "eq(return.count,5)",
                        },
                        "counter_example": {"staged_payload": {"parameters": {"limit": 3}}},
                        "validation_cases": [
                            {
                                "case_number": 1,
                                "verdict": "STATIC_WIN",
                                "request": {"parameters": {"limit": 3}},
                                "response_summary": {"status_code": 200},
                                "response_payload": {"count": 3, "large": ["hidden"]},
                                "static_evaluation": {
                                    "executed_expression": "gte(return.count, 0)",
                                    "result": True,
                                },
                                "dynamic_evaluation": {
                                    "executed_expression": "eq(return.count,5)",
                                    "result": False,
                                },
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    output = generate_combination_report(source)
    rendered = output.read_text(encoding="utf-8")

    assert output.name == "combine_constraint_miners.html"
    assert "Combined Constraint Report" in rendered
    assert "All statuses" in rendered
    assert "STATIC_WIN" in rendered
    assert "return.count" in rendered
    assert 'class="record"' in rendered
    assert "Runtime validation cases" in rendered
    assert "Static validation:" in rendered
    assert "Dynamic validation:" in rendered
    assert "Inspect response payload" in rendered
