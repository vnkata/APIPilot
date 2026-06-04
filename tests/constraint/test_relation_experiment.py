import json

from api_testing.constraint.relation_experiment import (
    GOLD_CASES,
    RelationCase,
    build_relation_cases,
    run_relation_experiment,
)
from api_testing.prompts.constraint_combination.schema import ConstraintCombinationVerdict


class FakeRelationModel:
    def __init__(self, relation: str = "EQUIVALENT"):
        self.relation = relation
        self.prompts: list[str] = []

    def generate(self, **kwargs):
        self.prompts.append(kwargs["prompt"])
        return (
            ConstraintCombinationVerdict(
                relation=self.relation,
                reason=f"{self.relation} from fake model.",
            ),
            None,
        )


def test_gold_benchmark_covers_subset_direction_traps():
    expected = {
        "gold-dynamic-stronger-exact-length-vs-nonempty": "DYNAMIC_STRONGER",
        "gold-dynamic-stronger-size-bound-vs-nonnegative": "DYNAMIC_STRONGER",
        "gold-dynamic-stronger-item-count-bound-vs-nonnegative": "DYNAMIC_STRONGER",
        "gold-static-stronger-code-enum-vs-length": "STATIC_STRONGER",
        "gold-static-stronger-nested-code-enum-vs-length": "STATIC_STRONGER",
        "gold-static-stronger-bounded-range-vs-lower-bound": "STATIC_STRONGER",
        "gold-partial-overlap-datetime-vs-raw-length": "PARTIAL_OVERLAP",
        "gold-partial-overlap-input-or-membership-vs-membership": "PARTIAL_OVERLAP",
        "gold-partial-overlap-date-year-guard-vs-format-only": "PARTIAL_OVERLAP",
        "gold-equivalent-url-plus-redundant-nonempty": "EQUIVALENT",
    }

    by_id = {case.case_id: case for case in GOLD_CASES}

    assert set(expected).issubset(by_id)
    assert {
        case_id: by_id[case_id].expected_relation for case_id in expected
    } == expected


def test_build_relation_cases_uses_combiner_canonical_property_matching():
    cases = build_relation_cases(
        static_constraints={
            "get-/things": {
                "return.items[].id": "gt(return.items[].id, 0)",
                "return.items[].name": "exists(return.items[].name)",
            }
        },
        dynamic_constraints={
            "get-/things": {
                "return.items.id": "return.items.id >= 1",
                "return.items.total": "return.items.total >= 0",
            }
        },
        source="unit",
    )

    assert cases == [
        RelationCase(
            case_id="unit:1",
            endpoint="get-/things",
            property="return.items[].id",
            static_constraint="gt(return.items[].id, 0)",
            dynamic_constraint="return.items.id >= 1",
            expected_relation=None,
            source="unit",
        )
    ]


def test_relation_experiment_writes_outputs_without_overwriting_source_cache(tmp_path):
    cache_dir = tmp_path / "source-cache"
    cache_dir.mkdir()
    combine_path = cache_dir / "combine_constraint_miners.json"
    combine_path.write_text('{"sentinel": true}', encoding="utf-8")
    (cache_dir / "static_constraint_miner.json").write_text(
        json.dumps(
            {
                "common": {
                    "get-/things": {
                        "return.id": "gt(return.id, 0)",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "dynamic_constraint_miner.json").write_text(
        json.dumps(
            {
                "constraints": {
                    "get-/things": {
                        "return.id": "return.id >= 1",
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    gold_cases = (
        RelationCase(
            case_id="gold-equivalent-id",
            endpoint="get-/things",
            property="return.id",
            static_constraint="gt(return.id, 0)",
            dynamic_constraint="return.id >= 1",
            expected_relation="EQUIVALENT",
            source="gold",
        ),
    )

    run_dir = run_relation_experiment(
        model=FakeRelationModel(),
        output_root=tmp_path / "_experiments" / "constraint_relation",
        run_id="unit-run",
        gold_cases=gold_cases,
        cache_dirs=[cache_dir],
        include_full=True,
    )

    assert combine_path.read_text(encoding="utf-8") == '{"sentinel": true}'
    assert (run_dir / "metadata.json").exists()
    gold_summary = json.loads((run_dir / "gold" / "summary.json").read_text("utf-8"))
    full_summary = json.loads((run_dir / "full" / "summary.json").read_text("utf-8"))
    assert gold_summary["accuracy"] == 1.0
    assert gold_summary["mismatches"] == []
    assert full_summary["total_cases"] == 1
    assert (run_dir / "gold" / "raw_prompts.jsonl").read_text("utf-8").strip()
    assert (run_dir / "gold" / "raw_responses.jsonl").read_text("utf-8").strip()
