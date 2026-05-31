import json

from api_testing.constraint.constraint_combiner import ConstraintCombiner
from api_testing.prompts.constraint_combination.schema import (
    ConstraintCombinationVerdict,
    CounterExamplePlan,
)


def test_combiner_matches_array_property_notation_and_keeps_unique_rules(tmp_path):
    combiner = ConstraintCombiner(cache_dir=tmp_path)
    result = combiner.combine(
        static_constraints={
            "get-/api/v1/BillTypes": {
                "return.items[].category": "in(return.items[].category, ['Public'])",
                "return.totalResults": "gte(return.totalResults, 0)",
            }
        },
        dynamic_constraints={
            "get-/api/v1/BillTypes": {
                "return.items.category": "in(return.items.category, ['Public'])",
                "return.items.id": "gte(return.items.id, 1)",
            }
        },
    )

    properties = result["get-/api/v1/BillTypes"]
    paired = properties["return.items[].category"]
    assert paired["status"] == "COMBINED_EQUIVALENT"
    assert paired["static_constraint"] == "in(return.items[].category, ['Public'])"
    assert paired["dynamic_constraint"] == "in(return.items.category, ['Public'])"
    assert properties["return.totalResults"]["status"] == "UNIQUE_STATIC"
    assert properties["return.items.id"]["status"] == "UNIQUE_DYNAMIC"

    output = json.loads((tmp_path / "combine_constraint_miners.json").read_text(encoding="utf-8"))
    assert output == result


def test_combiner_keeps_non_equivalent_pair_pending_without_model(tmp_path):
    combiner = ConstraintCombiner(cache_dir=tmp_path)
    result = combiner.combine(
        static_constraints={"get-/things": {"return.count": "gte(return.count, 0)"}},
        dynamic_constraints={"get-/things": {"return.count": "eq(return.count, 5)"}},
    )

    record = result["get-/things"]["return.count"]
    assert record["status"] == "NOT_COMBINED"
    assert record["final_constraint"] is None
    assert record["counter_example"] is None


class FakeModel:
    def generate(self, **kwargs):
        assert "gt(return.id, 0)" in kwargs["prompt"]
        return (
            ConstraintCombinationVerdict(
                status="COMBINED_EQUIVALENT",
                final_constraint="gt(return.id, 0)",
                reason="Integer lower bounds are equivalent.",
            ),
            None,
        )


def test_combiner_uses_model_for_non_textual_equivalence(tmp_path):
    combiner = ConstraintCombiner(cache_dir=tmp_path, model=FakeModel())
    result = combiner.combine(
        static_constraints={"get-/things": {"return.id": "gt(return.id, 0)"}},
        dynamic_constraints={"get-/things": {"return.id": "return.id >= 1"}},
    )

    record = result["get-/things"]["return.id"]
    assert record["status"] == "COMBINED_EQUIVALENT"
    assert record["final_constraint"] == "gt(return.id, 0)"


class ConflictModel:
    def generate(self, **kwargs):
        return (
            ConstraintCombinationVerdict(
                status="NOT_COMBINED",
                final_constraint=None,
                reason="The dynamic equality is narrower than the specification lower bound.",
                counter_example=CounterExamplePlan(
                    target_side="STATIC_TRUE_DYNAMIC_FALSE",
                    concrete_property_value=3,
                    staged_payload={
                        "http_method": "GET",
                        "endpoint_path": "/things",
                        "parameters": {"limit": 3},
                    },
                    staged_payloads=[
                        {"http_method": "GET", "endpoint_path": "/things", "parameters": {"limit": 3}},
                        {"http_method": "GET", "endpoint_path": "/things", "parameters": {"limit": 4}},
                    ],
                ),
            ),
            None,
        )


def test_combiner_stages_model_detected_conflict(tmp_path):
    result = ConstraintCombiner(cache_dir=tmp_path, model=ConflictModel()).combine(
        static_constraints={"get-/things": {"return.count": "gte(return.count, 0)"}},
        dynamic_constraints={"get-/things": {"return.count": "eq(return.count, 5)"}},
    )

    record = result["get-/things"]["return.count"]
    assert record["status"] == "NOT_COMBINED"
    assert record["final_constraint"] is None
    assert record["counter_example"]["concrete_property_value"] == 3
    assert len(record["counter_example"]["staged_payloads"]) == 2
