"""
Description pattern catalog for rule-based constraint extraction.

Defines regex patterns for extracting constraints from natural language
descriptions with high precision.
"""

import re
from typing import Any


class DescriptionPattern:
    """Single description pattern for constraint extraction."""

    def __init__(
        self,
        name: str,
        pattern: str,
        predicate_kind: str,
        args_builder: callable,
        confidence: float = 0.95,
    ):
        """Initialize pattern.

        Args:
            name: Pattern name
            pattern: Regex pattern (case-insensitive)
            predicate_kind: Target predicate kind
            args_builder: Function to build predicate args from match
            confidence: Confidence score (0.0-1.0)
        """
        self.name = name
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.predicate_kind = predicate_kind
        self.args_builder = args_builder
        self.confidence = confidence

    def match(self, description: str) -> tuple[dict[str, Any], str] | None:
        """Try to match pattern against description.

        Args:
            description: Description text

        Returns:
            Tuple of (args_dict, evidence) or None if no match
        """
        m = self.pattern.search(description)
        if m:
            try:
                args = self.args_builder(m)
                evidence = m.group(0)
                return (args, evidence)
            except Exception:
                return None
        return None


# ============================================================================
# Pattern Definitions
# ============================================================================


def _build_range_args(match: re.Match) -> dict:
    """Build range args from match."""
    return {
        "min": int(match.group(1)),
        "max": int(match.group(2)),
    }


def _build_values_list_args(match: re.Match) -> dict:
    """Build enum values from match."""
    values_str = match.group(1)
    # Parse values (handles ['A', 'B'] or [1, 2])
    values = eval(values_str)  # Safe here as we control the pattern
    return {"values": values}


def _build_uri_scheme_args(match: re.Match) -> dict:
    """Build URI args with scheme restriction."""
    scheme = match.group(1) if match.lastindex >= 1 else "https"
    return {"allowed_schemes": [scheme]}


def _build_pattern_args(match: re.Match) -> dict:
    """Build pattern args."""
    pattern = match.group(1)
    return {"pattern": pattern}


def _build_length_args(match: re.Match) -> dict:
    """Build string length args."""
    if match.lastindex == 2:
        return {"min": int(match.group(1)), "max": int(match.group(2))}
    elif "min" in match.group(0).lower():
        return {"min": int(match.group(1))}
    else:
        return {"max": int(match.group(1))}


# Integer patterns
INTEGER_RANGE_PATTERNS = [
    DescriptionPattern(
        name="int_between",
        pattern=r"(?:integer|number|int)?\s*between\s+(\d+)\s+and\s+(\d+)",
        predicate_kind="int.range",
        args_builder=_build_range_args,
    ),
    DescriptionPattern(
        name="int_from_to",
        pattern=r"(?:from|minimum|min)\s+(\d+)\s+to\s+(\d+)(?:\s+maximum|max)?",
        predicate_kind="int.range",
        args_builder=_build_range_args,
    ),
    DescriptionPattern(
        name="int_min_max",
        pattern=r"min(?:imum)?[:\s]+(\d+).*max(?:imum)?[:\s]+(\d+)",
        predicate_kind="int.range",
        args_builder=_build_range_args,
    ),
]

INTEGER_ENUM_PATTERNS = [
    DescriptionPattern(
        name="int_values_in_of",
        pattern=r"values?\s+in\s+of\s+(\[[0-9,\s]+\])",
        predicate_kind="int.enum",
        args_builder=_build_values_list_args,
    ),
    DescriptionPattern(
        name="int_one_of",
        pattern=r"one\s+of[:\s]+(\[[0-9,\s]+\])",
        predicate_kind="int.enum",
        args_builder=_build_values_list_args,
    ),
]

# String patterns
STRING_ENUM_PATTERNS = [
    DescriptionPattern(
        name="str_values_in_of",
        pattern=r"values?\s+in\s+of\s+(\[[\'\"][^\]]+\])",
        predicate_kind="string.enum",
        args_builder=_build_values_list_args,
    ),
    DescriptionPattern(
        name="str_one_of",
        pattern=r"one\s+of[:\s]+(\[[\'\"][^\]]+\])",
        predicate_kind="string.enum",
        args_builder=_build_values_list_args,
    ),
    DescriptionPattern(
        name="str_must_be_one_of",
        pattern=r"must\s+be\s+one\s+of[:\s]+(\[[\'\"][^\]]+\])",
        predicate_kind="string.enum",
        args_builder=_build_values_list_args,
    ),
]

STRING_FORMAT_PATTERNS = [
    DescriptionPattern(
        name="iso_date",
        pattern=r"ISO\s+(?:8601\s+)?date|date\s+format|YYYY-MM-DD",
        predicate_kind="date.iso_date",
        args_builder=lambda m: {},
    ),
    DescriptionPattern(
        name="iso_datetime",
        pattern=r"ISO\s+(?:8601\s+)?datetime|datetime\s+format|RFC\s+3339",
        predicate_kind="date.iso_datetime",
        args_builder=lambda m: {},
    ),
    DescriptionPattern(
        name="uri_https",
        pattern=r"(?:valid\s+)?URI\s+starting\s+with\s+(https?)|^https?\s+URI",
        predicate_kind="string.uri",
        args_builder=_build_uri_scheme_args,
    ),
    DescriptionPattern(
        name="email",
        pattern=r"(?:valid\s+)?email\s+address|email\s+format",
        predicate_kind="string.email",
        args_builder=lambda m: {},
    ),
    DescriptionPattern(
        name="uuid",
        pattern=r"(?:valid\s+)?UUID|universally\s+unique\s+identifier",
        predicate_kind="string.uuid",
        args_builder=lambda m: {},
    ),
]

STRING_PATTERN_PATTERNS = [
    DescriptionPattern(
        name="pattern",
        pattern=r"pattern[:\s]+([\w\+\-\^\$\.\*\[\]]+)",
        predicate_kind="string.pattern",
        args_builder=_build_pattern_args,
        confidence=0.9,
    ),
    DescriptionPattern(
        name="must_start_with",
        pattern=r"must\s+start\s+with\s+['\"]?([^'\"]+)['\"]?",
        predicate_kind="string.pattern",
        args_builder=lambda m: {"pattern": f"^{re.escape(m.group(1))}"},
        confidence=0.85,
    ),
]

STRING_LENGTH_PATTERNS = [
    DescriptionPattern(
        name="length_between",
        pattern=r"length\s+between\s+(\d+)\s+and\s+(\d+)",
        predicate_kind="string.length",
        args_builder=_build_length_args,
    ),
    DescriptionPattern(
        name="max_length",
        pattern=r"max(?:imum)?\s+length[:\s]+(\d+)",
        predicate_kind="string.length",
        args_builder=_build_length_args,
    ),
    DescriptionPattern(
        name="min_length",
        pattern=r"min(?:imum)?\s+length[:\s]+(\d+)",
        predicate_kind="string.length",
        args_builder=_build_length_args,
    ),
]

# Number patterns
NUMBER_RANGE_PATTERNS = [
    DescriptionPattern(
        name="num_between",
        pattern=r"(?:number|float|double)?\s*between\s+([\d.]+)\s+and\s+([\d.]+)",
        predicate_kind="number.range",
        args_builder=lambda m: {"min": float(m.group(1)), "max": float(m.group(2))},
    ),
]

# Array patterns
ARRAY_LENGTH_PATTERNS = [
    DescriptionPattern(
        name="array_min_max_items",
        pattern=r"min(?:imum)?\s+(\d+).*max(?:imum)?\s+(\d+)\s+items",
        predicate_kind="array.length",
        args_builder=_build_range_args,
    ),
]

# Boolean patterns
BOOLEAN_PATTERNS = [
    DescriptionPattern(
        name="must_be_true",
        pattern=r"must\s+be\s+true|always\s+true",
        predicate_kind="boolean.const",
        args_builder=lambda m: {"value": True},
    ),
    DescriptionPattern(
        name="must_be_false",
        pattern=r"must\s+be\s+false|always\s+false",
        predicate_kind="boolean.const",
        args_builder=lambda m: {"value": False},
    ),
]


# ============================================================================
# Pattern Registry
# ============================================================================


ALL_PATTERNS: list[DescriptionPattern] = (
    INTEGER_RANGE_PATTERNS
    + INTEGER_ENUM_PATTERNS
    + STRING_ENUM_PATTERNS
    + STRING_FORMAT_PATTERNS
    + STRING_PATTERN_PATTERNS
    + STRING_LENGTH_PATTERNS
    + NUMBER_RANGE_PATTERNS
    + ARRAY_LENGTH_PATTERNS
    + BOOLEAN_PATTERNS
)


def match_patterns(
    description: str, field_type: str | None = None
) -> list[tuple[DescriptionPattern, dict, str]]:
    """Match description against all patterns.

    Args:
        description: Description text
        field_type: Optional field type for filtering patterns

    Returns:
        List of (pattern, args, evidence) tuples
    """
    matches = []

    for pattern in ALL_PATTERNS:
        # Filter by field type if provided
        if field_type:
            if field_type == "integer" and not pattern.predicate_kind.startswith(
                "int."
            ):
                continue
            if field_type == "string" and not pattern.predicate_kind.startswith(
                ("string.", "date.")
            ):
                continue
            if field_type == "number" and not pattern.predicate_kind.startswith(
                "number."
            ):
                continue
            if field_type == "array" and not pattern.predicate_kind.startswith(
                "array."
            ):
                continue
            if field_type == "boolean" and not pattern.predicate_kind.startswith(
                "boolean."
            ):
                continue

        result = pattern.match(description)
        if result:
            args, evidence = result
            matches.append((pattern, args, evidence))

    return matches


__all__ = [
    "DescriptionPattern",
    "ALL_PATTERNS",
    "match_patterns",
]
