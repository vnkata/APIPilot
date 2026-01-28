"""Date validators."""

from typing import Any, Dict, List
from datetime import datetime
from api_testing.constraint.ir.core import ViolationModel


def date_iso_date_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate strings are valid ISO 8601 dates (YYYY-MM-DD)."""
    violations = []

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date.iso_date@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if "T" in value or " " in value:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date.iso_date@v1",
                    message=f"Value '{value}' appears to be a datetime, not a date",
                    path=ctx.get("path", ""),
                    value=value,
                    expected="YYYY-MM-DD format",
                )
            )
            continue

        try:
            datetime.fromisoformat(value)
        except (ValueError, TypeError) as e:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date.iso_date@v1",
                    message=f"Value '{value}' is not a valid ISO 8601 date: {str(e)}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected="YYYY-MM-DD format",
                )
            )

    return violations


def date_iso_datetime_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate strings are valid ISO 8601 datetimes."""
    violations = []

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date.iso_datetime@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date.iso_datetime@v1",
                    message=f"Value '{value}' is not a valid ISO 8601 datetime: {str(e)}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )

    return violations


__all__ = ["date_iso_date_v1", "date_iso_datetime_v1"]
