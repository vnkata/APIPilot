"""Common utilities for constraint extraction."""

from api_testing.constraint.ir.extractors.common.candidate_constraint import (
    CandidateConstraint,
    Evidence,
)
from api_testing.constraint.ir.extractors.common.coverage_models import (
    CoverageCheckResult,
)
from api_testing.constraint.ir.extractors.common.description_patterns import (
    match_patterns,
)
from api_testing.constraint.ir.extractors.common.name_matching import (
    are_related_by_naming,
    calculate_similarity,
    extract_base_name,
    extract_entity_name,
    find_best_match,
    is_id_field,
    normalize_name,
    to_camel_case,
    to_snake_case,
)

__all__ = [
    "Evidence",
    "CandidateConstraint",
    "CoverageCheckResult",
    "normalize_name",
    "to_snake_case",
    "to_camel_case",
    "extract_base_name",
    "calculate_similarity",
    "find_best_match",
    "is_id_field",
    "extract_entity_name",
    "are_related_by_naming",
    "match_patterns",
]
