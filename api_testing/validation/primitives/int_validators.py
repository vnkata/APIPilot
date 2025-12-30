"""
Integer validators for constraint validation.

Provides validators for:
- int.range@v1: Validate integer is within [min, max] range
- int.enum@v1: Validate integer is in allowed enum values
"""

from typing import Any, Dict, List
from api_testing.validation.models import Violation, ValidationContext


def int_range_v1(
    value: Any, args: Dict[str, Any], ctx: ValidationContext
) -> List[Violation]:
    """Validate integer is within [min, max] range.

    Args:
        value: Value to validate
        args: {"min": int (optional), "max": int (optional)}
        ctx: Validation context

    Returns:
        List of violations (empty if valid)
    """
    # Type check (exclude bool which is subclass of int in Python)
    if not isinstance(value, int) or isinstance(value, bool):
        return [
            Violation(
                kind="int.range@v1",
                message=f"Expected integer, got {type(value).__name__}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    violations = []
    min_val = args.get("min")
    max_val = args.get("max")

    if min_val is not None and value < min_val:
        violations.append(
            Violation(
                kind="int.range@v1",
                message=f"Value {value} is less than minimum {min_val}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        )

    if max_val is not None and value > max_val:
        violations.append(
            Violation(
                kind="int.range@v1",
                message=f"Value {value} exceeds maximum {max_val}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        )

    return violations


def int_enum_v1(
    value: Any, args: Dict[str, Any], ctx: ValidationContext
) -> List[Violation]:
    """Validate integer is in allowed enum values.

    Args:
        value: Value to validate
        args: {"values": List[int]}
        ctx: Validation context

    Returns:
        List of violations (empty if valid)
    """
    # Type check (exclude bool which is subclass of int in Python)
    if not isinstance(value, int) or isinstance(value, bool):
        return [
            Violation(
                kind="int.enum@v1",
                message=f"Expected integer, got {type(value).__name__}",
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
                kind="int.enum@v1",
                message="No allowed values specified in validator args",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    if value not in allowed_values:
        return [
            Violation(
                kind="int.enum@v1",
                message=f"Value {value} not in allowed values {allowed_values}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    return []


__all__ = ["int_range_v1", "int_enum_v1"]
