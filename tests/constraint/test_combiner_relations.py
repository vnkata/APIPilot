import json

import pytest
from pydantic import ValidationError

from api_testing.constraint.constraint_combiner import ConstraintCombiner
from api_testing.prompts.constraint_combination import ConstraintCombination
from api_testing.prompts.constraint_combination.schema import ConstraintCombinationVerdict


class RelationModel:
    def __init__(self, relations: dict[str, str]):
        self.relations = relations
        self.prompts: list[str] = []

    def generate(self, **kwargs):
        prompt = kwargs["prompt"]
        self.prompts.append(prompt)
        property_name = next(
            key for key in self.relations if f"Property: {key}" in prompt
        )
        relation = self.relations[property_name]
        return (
            ConstraintCombinationVerdict(
                relation=relation,
                reason=f"{relation} relation selected by the test model.",
            ),
            None,
        )


class FailingOnceModel:
    def __init__(self):
        self.prompts: list[str] = []

    def generate(self, **kwargs):
        prompt = kwargs["prompt"]
        self.prompts.append(prompt)
        if "Property: return.a" in prompt:
            raise RuntimeError("synthetic parse failure")
        return (
            ConstraintCombinationVerdict(
                relation="EQUIVALENT",
                reason="Recovered on the next property.",
            ),
            None,
        )


@pytest.mark.parametrize(
    ("relation", "expected_status", "expected_final"),
    [
        ("EQUIVALENT", "RESOLVED", "static-rule"),
        ("STATIC_STRONGER", "UNRESOLVED", None),
        ("DYNAMIC_STRONGER", "UNRESOLVED", None),
        ("PARTIAL_OVERLAP", "UNRESOLVED", None),
        ("DISJOINT", "CONFLICT", None),
        ("UNKNOWN", "UNRESOLVED", None),
    ],
)
def test_combiner_derives_status_and_final_constraint_from_llm_relation(
    tmp_path, relation, expected_status, expected_final
):
    model = RelationModel({"return.value": relation})

    result = ConstraintCombiner(cache_dir=tmp_path, model=model).combine(
        static_constraints={"get-/things": {"return.value": "static-rule"}},
        dynamic_constraints={"get-/things": {"return.value": "dynamic-rule"}},
    )

    record = result["get-/things"]["return.value"]
    assert record["relation"] == relation
    assert record["status"] == expected_status
    assert record["final_constraint"] == expected_final
    assert record["runtime_verdict"] is None
    assert record["counter_example"] is None
    assert "verdict" not in record


def test_combination_schema_rejects_classifier_counter_example_payload():
    with pytest.raises(ValidationError):
        ConstraintCombinationVerdict.model_validate(
            {
                "relation": "PARTIAL_OVERLAP",
                "reason": "The sets overlap.",
                "counter_example": {"staged_payload": {"parameters": {"x": 1}}},
            }
        )


def test_combination_prompt_is_classification_only():
    system_prompt = ConstraintCombination.SYSTEM_PROMPT

    assert "counter_example" not in system_prompt
    assert "staged_payload" not in system_prompt
    assert "runtime winner" not in system_prompt.lower()
    assert "UNKNOWN" in system_prompt
    assert "Decision checklist" in system_prompt
    assert "Generic examples" in system_prompt
    assert "strict subset" in system_prompt
    assert "exists(x)" in system_prompt
    assert "exact string length" in system_prompt
    assert "no dynamic-valid" in system_prompt
    assert "observed often enough" in system_prompt
    assert 'isURL("")` is false' in system_prompt
    assert "Never treat a finite enum and a length check as equivalent" in system_prompt
    assert "x >= size(collection)" in system_prompt
    assert "OR membership in a collection" in system_prompt
    assert "input-year equality" in system_prompt
    assert "LENGTH(x)==6" in system_prompt


def test_combiner_calls_llm_even_when_expressions_match_textually(tmp_path):
    model = RelationModel({"return.id": "EQUIVALENT"})

    result = ConstraintCombiner(cache_dir=tmp_path, model=model).combine(
        static_constraints={"get-/things": {"return.id": "eq(return.id, 1)"}},
        dynamic_constraints={"get-/things": {"return.id": "eq(return.id, 1)"}},
    )

    record = result["get-/things"]["return.id"]
    assert len(model.prompts) == 1
    assert record["status"] == "RESOLVED"
    assert record["relation"] == "EQUIVALENT"
    assert record["final_constraint"] == "eq(return.id, 1)"


def test_single_llm_failure_does_not_disable_remaining_pair_classification(tmp_path):
    model = FailingOnceModel()

    result = ConstraintCombiner(cache_dir=tmp_path, model=model).combine(
        static_constraints={
            "get-/things": {
                "return.a": "static-a",
                "return.b": "static-b",
            }
        },
        dynamic_constraints={
            "get-/things": {
                "return.a": "dynamic-a",
                "return.b": "dynamic-b",
            }
        },
    )

    first = result["get-/things"]["return.a"]
    second = result["get-/things"]["return.b"]
    assert len(model.prompts) == 2
    assert first["status"] == "UNRESOLVED"
    assert first["relation"] == "UNKNOWN"
    assert first["final_constraint"] is None
    assert first["counter_example"] is None
    assert second["status"] == "RESOLVED"
    assert second["relation"] == "EQUIVALENT"
    assert second["final_constraint"] == "static-b"


def test_combiner_keeps_unique_rules_with_null_relation(tmp_path):
    result = ConstraintCombiner(cache_dir=tmp_path).combine(
        static_constraints={"get-/things": {"return.total": "gte(return.total, 0)"}},
        dynamic_constraints={"get-/things": {"return.id": "gte(return.id, 1)"}},
    )

    properties = result["get-/things"]
    assert properties["return.total"]["status"] == "UNIQUE_STATIC"
    assert properties["return.total"]["relation"] is None
    assert properties["return.total"]["final_constraint"] == "gte(return.total, 0)"
    assert properties["return.id"]["status"] == "UNIQUE_DYNAMIC"
    assert properties["return.id"]["relation"] is None
    assert properties["return.id"]["final_constraint"] == "gte(return.id, 1)"

    output = json.loads(
        (tmp_path / "combine_constraint_miners.json").read_text(encoding="utf-8")
    )
    assert output == result


def test_combiner_marks_pair_unresolved_when_llm_is_unavailable(tmp_path):
    result = ConstraintCombiner(cache_dir=tmp_path).combine(
        static_constraints={"get-/things": {"return.count": "gte(return.count, 0)"}},
        dynamic_constraints={"get-/things": {"return.count": "return.count == 5"}},
    )

    record = result["get-/things"]["return.count"]
    assert record["status"] == "UNRESOLVED"
    assert record["relation"] == "UNKNOWN"
    assert record["final_constraint"] is None
    assert record["counter_example"] is None
