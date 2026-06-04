import json
from pathlib import Path

from api_testing.constraint.counter_example_experiment import (
    GOLD_CASES,
    CounterExampleExperimentCase,
    build_counter_example_cases_from_combine,
    run_counter_example_experiment,
)

LABEL_FIXTURE = Path("docs/ai/prompt-regression-labels/counter-example-planner.jsonl")


class FakePlanner:
    def __init__(self):
        self.contexts = []
        self.last_interactions = []
        self.last_error = None

    def generate(self, context):
        self.contexts.append(context)
        vector = context.get("expected_target_truth_vector") or {
            "static_constraint": "unknown",
            "dynamic_constraint": "unknown",
        }
        self.last_interactions = [
            {
                "case_id": context["case_id"],
                "attempt": 1,
                "system_prompt": "fake system",
                "prompt": "fake prompt",
                "parsed_response": {
                    "cases": [
                        {
                            "case_id": f"{context['case_id']}-draft",
                            "request": {"method": "GET", "path": "/things"},
                            "target_truth_vector": vector,
                            "rationale": "Fake draft.",
                            "risk": "low",
                            "expected_observation": "Fake observation.",
                        }
                    ]
                },
                "error": None,
            }
        ]
        return self.last_interactions[0]["parsed_response"]["cases"]


def test_counter_example_gold_cases_cover_expected_relations_and_targets():
    assert len(GOLD_CASES) >= 20

    relations = {case.relation for case in GOLD_CASES}
    assert {
        "DYNAMIC_STRONGER",
        "STATIC_STRONGER",
        "PARTIAL_OVERLAP",
        "DISJOINT",
        "UNKNOWN",
    }.issubset(relations)
    for case in GOLD_CASES:
        assert set(case.expected_target_truth_vector) == {
            "static_constraint",
            "dynamic_constraint",
        }


def test_counter_example_prompt_regression_labels_are_sanitized_jsonl():
    rows = [
        json.loads(line)
        for line in LABEL_FIXTURE.read_text("utf-8").splitlines()
        if line.strip()
    ]

    assert len(rows) >= 6
    for row in rows:
        assert {"case_id", "relation", "expected_target_truth_vector"}.issubset(row)
        assert set(row["expected_target_truth_vector"]) == {
            "static_constraint",
            "dynamic_constraint",
        }
        assert "raw_prompt" not in row
        assert "raw_response" not in row


def test_build_counter_example_cases_from_new_combine_artifact():
    cases = build_counter_example_cases_from_combine(
        {
            "get-/things": {
                "return.id": {
                    "endpoint": "get-/things",
                    "property": "return.id",
                    "static_constraint": "exists(return.id)",
                    "dynamic_constraint": "return.id >= 1",
                    "relation": "DYNAMIC_STRONGER",
                    "status": "UNRESOLVED",
                    "runtime_verdict": None,
                    "final_constraint": None,
                }
            }
        },
        source="unit",
    )

    assert cases == [
        CounterExampleExperimentCase(
            case_id="unit:1",
            endpoint="get-/things",
            property="return.id",
            static_constraint="exists(return.id)",
            dynamic_constraint="return.id >= 1",
            relation="DYNAMIC_STRONGER",
            status="UNRESOLVED",
            expected_target_truth_vector=None,
            source="unit",
            record={
                "endpoint": "get-/things",
                "property": "return.id",
                "static_constraint": "exists(return.id)",
                "dynamic_constraint": "return.id >= 1",
                "relation": "DYNAMIC_STRONGER",
                "status": "UNRESOLVED",
                "runtime_verdict": None,
                "final_constraint": None,
            },
        )
    ]


def test_counter_example_experiment_writes_outputs_without_overwriting_cache(tmp_path):
    cache_dir = tmp_path / "source-cache"
    cache_dir.mkdir()
    combine_path = cache_dir / "combine_constraint_miners.json"
    combine_path.write_text(
        json.dumps(
            {
                "get-/things": {
                    "return.id": {
                        "endpoint": "get-/things",
                        "property": "return.id",
                        "static_constraint": "exists(return.id)",
                        "dynamic_constraint": "return.id >= 1",
                        "relation": "DYNAMIC_STRONGER",
                        "status": "UNRESOLVED",
                        "runtime_verdict": None,
                        "final_constraint": None,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "specification.json").write_text(
        json.dumps({"paths": {"/things": {"get": {"operationId": "getThings"}}}}),
        encoding="utf-8",
    )
    (cache_dir / "reports.json").write_text("[]", encoding="utf-8")
    (cache_dir / "test_cases.json").write_text("[]", encoding="utf-8")
    gold_cases = (
        CounterExampleExperimentCase(
            case_id="gold-static-only",
            endpoint="get-/things",
            property="return.id",
            static_constraint="exists(return.id)",
            dynamic_constraint="return.id >= 1",
            relation="DYNAMIC_STRONGER",
            status="UNRESOLVED",
            expected_target_truth_vector={
                "static_constraint": "true",
                "dynamic_constraint": "false",
            },
            source="gold",
        ),
    )

    run_dir = run_counter_example_experiment(
        planner=FakePlanner(),
        output_root=tmp_path / "_experiments" / "counter_examples",
        run_id="unit-run",
        gold_cases=gold_cases,
        cache_dirs=[cache_dir],
        include_full=True,
    )

    assert json.loads(combine_path.read_text("utf-8"))["get-/things"]["return.id"][
        "relation"
    ] == "DYNAMIC_STRONGER"
    assert (run_dir / "metadata.json").exists()
    assert (run_dir / "cases.jsonl").read_text("utf-8").strip()
    assert (run_dir / "raw_prompts_responses.jsonl").read_text("utf-8").strip()
    assert (run_dir / "mismatch_report.md").exists()
    summary = json.loads((run_dir / "summary.json").read_text("utf-8"))
    assert summary["total_cases"] == 2
    assert summary["gold_cases"] == 1
    assert summary["gold_matches"] == 1
    assert summary["gold_accuracy"] == 1.0
