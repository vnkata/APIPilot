"""
String validators for constraint validation.

Provides validators for:
- string.enum@v1: Validate string is in allowed enum values
- string.pattern@v1: Validate string matches regex pattern
"""

import re
from typing import Any, Dict, List
from api_testing.validation.models import Violation, ValidationContext


def string_enum_v1(
    value: Any, args: Dict[str, Any], ctx: ValidationContext
) -> List[Violation]:
    """Validate string is in allowed enum values.

    Args:
        value: Value to validate
        args: {"values": List[str]}
        ctx: Validation context

    Returns:
        List of violations (empty if valid)
    """
    # Type check
    if not isinstance(value, str):
        return [
            Violation(
                kind="string.enum@v1",
                message=f"Expected string, got {type(value).__name__}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    allowed_values = args.get("values", [])
    if not allowed_values:
        return [
            Violation(
                kind="string.enum@v1",
                message="No allowed values specified in validator args",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    # Validate all values are strings
    if not all(isinstance(v, str) for v in allowed_values):
        return [
            Violation(
                kind="string.enum@v1",
                message="Invalid validator args: values must be list of strings",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    if value not in allowed_values:
        # Truncate long enum lists in error message
        values_display = (
            allowed_values
            if len(allowed_values) <= 10
            else allowed_values[:10] + ["..."]
        )
        return [
            Violation(
                kind="string.enum@v1",
                message=f"Value '{value}' not in allowed values {values_display}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    return []


def string_pattern_v1(
    value: Any, args: Dict[str, Any], ctx: ValidationContext
) -> List[Violation]:
    """Validate string matches regex pattern.

    Args:
        value: Value to validate
        args: {"pattern": str}
        ctx: Validation context

    Returns:
        List of violations (empty if valid)
    """
    # Type check
    if not isinstance(value, str):
        return [
            Violation(
                kind="string.pattern@v1",
                message=f"Expected string, got {type(value).__name__}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    pattern = args.get("pattern")
    if not pattern:
        return [
            Violation(
                kind="string.pattern@v1",
                message="No pattern specified in validator args",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    if not isinstance(pattern, str):
        return [
            Violation(
                kind="string.pattern@v1",
                message="Invalid validator args: pattern must be a string",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    try:
        if not re.match(pattern, value):
            return [
                Violation(
                    kind="string.pattern@v1",
                    message=f"Value '{value}' does not match pattern '{pattern}'",
                    path=ctx.path,
                    value=value,
                    op_key=ctx.op_key,
                    severity="error",
                )
            ]
    except re.error as e:
        return [
            Violation(
                kind="string.pattern@v1",
                message=f"Invalid regex pattern '{pattern}': {str(e)}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    return []


__all__ = ["string_enum_v1", "string_pattern_v1"]
