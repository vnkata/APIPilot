"""
Date validators for constraint validation.

Provides validators for:
- date.iso_date@v1: Validate string is valid ISO 8601 date (YYYY-MM-DD)
"""

from datetime import datetime
from typing import Any, Dict, List
from api_testing.validation.models import Violation, ValidationContext


def date_iso_date_v1(
    value: Any, args: Dict[str, Any], ctx: ValidationContext
) -> List[Violation]:
    """Validate string is valid ISO 8601 date (YYYY-MM-DD).

    Args:
        value: Value to validate
        args: {} (no args needed)
        ctx: Validation context

    Returns:
        List of violations (empty if valid)
    """
    # Type check
    if not isinstance(value, str):
        return [
            Violation(
                kind="date.iso_date@v1",
                message=f"Expected string, got {type(value).__name__}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    # Try to parse as ISO date (YYYY-MM-DD)
    try:
        datetime.fromisoformat(value)
        # Additional check: ensure it's just a date, not datetime
        if "T" in value or " " in value:
            return [
                Violation(
                    kind="date.iso_date@v1",
                    message=f"Value '{value}' appears to be a datetime, not a date (expected YYYY-MM-DD)",
                    path=ctx.path,
                    value=value,
                    op_key=ctx.op_key,
                    severity="error",
                )
            ]
    except (ValueError, TypeError) as e:
        return [
            Violation(
                kind="date.iso_date@v1",
                message=f"Value '{value}' is not a valid ISO 8601 date (expected YYYY-MM-DD): {str(e)}",
                path=ctx.path,
                value=value,
                op_key=ctx.op_key,
                severity="error",
            )
        ]

    return []


__all__ = ["date_iso_date_v1"]
