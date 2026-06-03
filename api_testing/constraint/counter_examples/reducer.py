"""Conservative runtime evidence reduction for counter-example executions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeEvidenceReduction:
    runtime_verdict: str
    runtime_recommendation: str
    reason: str


def reduce_runtime_evidence(
    *,
    relation: str | None,
    cases: list[dict[str, Any]],
) -> RuntimeEvidenceReduction:
    evaluated_cases = [
        case for case in cases if case.get("runtime_verdict") != "PROPERTY_NOT_PRESENT"
    ]
    verdicts = {str(case.get("runtime_verdict")) for case in evaluated_cases}
    if not verdicts:
        return RuntimeEvidenceReduction(
            runtime_verdict="INCONCLUSIVE_EVALUATION",
            runtime_recommendation="INCONCLUSIVE",
            reason="INCONCLUSIVE: Executed responses did not contain the target property.",
        )
    if "STATIC_WIN" in verdicts and "DYNAMIC_WIN" in verdicts:
        return RuntimeEvidenceReduction(
            runtime_verdict="INCONCLUSIVE_MIXED_EVIDENCE",
            runtime_recommendation="MIXED_EVIDENCE",
            reason="INCONCLUSIVE: Separate runtime cases supported opposite source constraints.",
        )
    if "STATIC_WIN" in verdicts:
        return RuntimeEvidenceReduction(
            runtime_verdict="STATIC_WIN",
            runtime_recommendation="SUPPORT_STATIC",
            reason=(
                "STATIC_WIN: At least one runtime case satisfied only the static "
                "constraint. Runtime evidence is support, not a formal proof."
            ),
        )
    if "DYNAMIC_WIN" in verdicts:
        recommendation = (
            "RELATION_CONTRADICTION"
            if relation == "DYNAMIC_STRONGER"
            else "SUPPORT_DYNAMIC"
        )
        reason = (
            "DYNAMIC_WIN: At least one runtime case satisfied only the dynamic "
            "constraint. Runtime evidence is support, not a formal proof."
        )
        if relation == "DYNAMIC_STRONGER":
            reason = (
                "RELATION_CONTRADICTION: A dynamic-only runtime case contradicts "
                "DYNAMIC_STRONGER set semantics. Review the relation classification "
                "or executable DSL mapping before accepting a final constraint."
            )
        return RuntimeEvidenceReduction(
            runtime_verdict="DYNAMIC_WIN",
            runtime_recommendation=recommendation,
            reason=reason,
        )
    if "CONFLICT_BOTH_FALSE" in verdicts:
        return RuntimeEvidenceReduction(
            runtime_verdict="CONFLICT_BOTH_FALSE",
            runtime_recommendation="MIXED_EVIDENCE",
            reason=(
                "CONFLICT_BOTH_FALSE: At least one runtime case violated both "
                "constraints or failed server-side."
            ),
        )
    if verdicts == {"BOTH_TRUE"}:
        return RuntimeEvidenceReduction(
            runtime_verdict="BOTH_TRUE",
            runtime_recommendation="INCONCLUSIVE",
            reason=(
                f"BOTH_TRUE: All {len(evaluated_cases)} evaluable runtime case(s) "
                "satisfied both constraints. Runtime evidence is support, not a formal proof."
            ),
        )
    if "BOTH_TRUE" in verdicts:
        return RuntimeEvidenceReduction(
            runtime_verdict="INCONCLUSIVE_PARTIAL_EVIDENCE",
            runtime_recommendation="INCONCLUSIVE",
            reason=(
                "INCONCLUSIVE: Valid cases satisfied both constraints, but other cases "
                "could not be evaluated conclusively."
            ),
        )
    if "INCONCLUSIVE_HTTP_STATUS" in verdicts:
        return RuntimeEvidenceReduction(
            runtime_verdict="INCONCLUSIVE_HTTP_STATUS",
            runtime_recommendation="INCONCLUSIVE",
            reason="INCONCLUSIVE: Counter-example requests returned no evaluable 2xx response.",
        )
    return RuntimeEvidenceReduction(
        runtime_verdict="INCONCLUSIVE_EVALUATION",
        runtime_recommendation="INCONCLUSIVE",
        reason="INCONCLUSIVE: Runtime responses could not be evaluated by the rule engine.",
    )
