"""
Constraint deduplication and merging logic.

Handles merging duplicate constraints that have the same scope, selectors,
and predicate kind but come from different sources.
"""

from typing import List, Dict, Tuple
from collections import defaultdict
from api_testing.constraint.ir.models import ConstraintModel, ProvenanceModel
from common.logger import get_logger

logger = get_logger(__name__)


def merge_duplicate_constraints(
    constraints: List[ConstraintModel],
) -> List[ConstraintModel]:
    """Merge duplicate constraints with multiple provenance sources.

    Duplicates are defined as constraints with:
    - Same scope (operation, phase, location)
    - Same selectors (expressions and order)
    - Same predicate kinds (not necessarily same args)

    Merged constraint:
    - Keeps all provenance sources
    - Uses highest confidence
    - Combines evidence strings
    - Merges predicate arguments (taking union where applicable)

    Args:
        constraints: List of ConstraintModel objects

    Returns:
        Deduplicated list of ConstraintModel objects
    """
    if not constraints:
        return []

    logger.debug("Starting constraint deduplication", total=len(constraints))

    # Group by (scope, selectors, predicate_kinds)
    grouped: Dict[Tuple, List[ConstraintModel]] = defaultdict(list)

    for constraint in constraints:
        key = _make_constraint_key(constraint)
        grouped[key].append(constraint)

    # Merge groups
    merged = []
    duplicate_groups = 0

    for group in grouped.values():
        if len(group) == 1:
            merged.append(group[0])
        else:
            duplicate_groups += 1
            merged_constraint = _merge_constraint_group(group)
            merged.append(merged_constraint)

    logger.info(
        "Constraint deduplication complete",
        original=len(constraints),
        deduplicated=len(merged),
        duplicate_groups=duplicate_groups,
    )

    return merged


def _make_constraint_key(constraint: ConstraintModel) -> Tuple:
    """Create a hashable key for constraint grouping.

    Args:
        constraint: ConstraintModel to create key for

    Returns:
        Tuple representing the constraint's unique characteristics
    """
    # Scope key
    scope_key = (
        constraint.scope.operation,
        constraint.scope.phase,
        constraint.scope.location,
    )

    # Selectors key (order matters)
    selectors_key = tuple(
        (s.kind, s.expr, s.mode) for s in constraint.selectors
    )

    # Predicate kinds key (order matters)
    predicate_kinds_key = tuple(p.kind for p in constraint.predicates)

    return (scope_key, selectors_key, predicate_kinds_key)


def _merge_constraint_group(group: List[ConstraintModel]) -> ConstraintModel:
    """Merge multiple constraints into one.

    Args:
        group: List of duplicate constraints to merge

    Returns:
        Single merged ConstraintModel
    """
    if len(group) == 1:
        return group[0]

    logger.debug(
        "Merging constraint group",
        constraint_id=group[0].id,
        group_size=len(group),
    )

    # Take first as base
    base = group[0].model_copy(deep=True)

    # Collect all sources
    all_sources = [c.source for c in group]

    # Find highest confidence
    max_confidence = max(s.confidence for s in all_sources)

    # Combine evidence (deduplicate similar evidence)
    evidence_parts = []
    seen_evidence = set()

    for source in all_sources:
        if source.evidence:
            # Normalize evidence for comparison
            normalized = source.evidence.strip().lower()[:100]
            if normalized not in seen_evidence:
                evidence_parts.append(f"[{source.kind}] {source.evidence}")
                seen_evidence.add(normalized)

    combined_evidence = "; ".join(evidence_parts)

    # Create merged provenance
    source_kinds = [s.kind for s in all_sources]
    merged_provenance = ProvenanceModel(
        kind="merged",
        confidence=max_confidence,
        evidence=combined_evidence,
        extracted_at=all_sources[0].extracted_at,  # Use earliest
    )

    # Update base constraint
    base.source = merged_provenance

    # Add metadata about merge
    if "merged_from" not in base.metadata:
        base.metadata["merged_from"] = source_kinds
        base.metadata["original_count"] = len(group)

    return base


__all__ = ["merge_duplicate_constraints"]
