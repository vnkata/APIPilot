"""Relation-aware counter-example planner strategies."""

from __future__ import annotations

from typing import Any, Mapping


class BaseCounterExamplePlannerStrategy:
    """Adds relation-specific diagnostic intent to a shared draft planner."""

    strategy_name = "generic_diagnostic"
    strategy_guidance = (
        "Generate a minimal diagnostic request that helps a reviewer compare "
        "the static and dynamic constraints without making a final decision."
    )

    def __init__(self, planner: Any, *, relation: str | None) -> None:
        self.planner = planner
        self.relation = relation
        self.prompt_version = getattr(planner, "prompt_version", None)

    def generate(self, context: Mapping[str, Any]) -> list[dict[str, Any]]:
        enriched = dict(context)
        enriched["planner_strategy"] = self.strategy_name
        enriched["planner_strategy_guidance"] = self.strategy_guidance
        return self.planner.generate(enriched)


class DynamicStrongerCounterExamplePlannerStrategy(BaseCounterExamplePlannerStrategy):
    strategy_name = "dynamic_stronger_diagnostic"
    strategy_guidance = (
        "Try to find a case where the broader static constraint is true while "
        "the stricter dynamic constraint is false. Runtime evidence remains "
        "support only and must not verify the dynamic constraint automatically."
    )


class StaticStrongerCounterExamplePlannerStrategy(BaseCounterExamplePlannerStrategy):
    strategy_name = "static_stronger_diagnostic"
    strategy_guidance = (
        "Try to find a case where the stricter static constraint is false while "
        "the broader dynamic constraint is true, or collect evidence that a "
        "reviewer can use to confirm the static-only restriction."
    )


class PartialOverlapCounterExamplePlannerStrategy(BaseCounterExamplePlannerStrategy):
    strategy_name = "partial_overlap_diagnostic"
    strategy_guidance = (
        "Try to find diagnostic cases around overlap boundaries: static-only, "
        "dynamic-only, and both-true cases when the operation context permits."
    )


class DisjointCounterExamplePlannerStrategy(BaseCounterExamplePlannerStrategy):
    strategy_name = "disjoint_diagnostic"
    strategy_guidance = (
        "Try to find a minimal case that reveals whether both constraints can "
        "be satisfied together or whether the relation classification conflicts "
        "with runtime behavior."
    )


class UnknownCounterExamplePlannerStrategy(BaseCounterExamplePlannerStrategy):
    strategy_name = "unknown_diagnostic"
    strategy_guidance = (
        "Generate a low-risk exploratory request that improves evidence for an "
        "under-specified relation. Do not recommend a final constraint."
    )


class GenericCounterExamplePlannerStrategy(BaseCounterExamplePlannerStrategy):
    pass


CounterExamplePlannerStrategy = BaseCounterExamplePlannerStrategy


def planner_strategy_for_relation(
    relation: str | None,
    planner: Any,
) -> BaseCounterExamplePlannerStrategy:
    strategy_type = {
        "STATIC_STRONGER": StaticStrongerCounterExamplePlannerStrategy,
        "DYNAMIC_STRONGER": DynamicStrongerCounterExamplePlannerStrategy,
        "PARTIAL_OVERLAP": PartialOverlapCounterExamplePlannerStrategy,
        "DISJOINT": DisjointCounterExamplePlannerStrategy,
        "UNKNOWN": UnknownCounterExamplePlannerStrategy,
    }.get(relation, GenericCounterExamplePlannerStrategy)
    return strategy_type(planner, relation=relation)
