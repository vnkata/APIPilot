"""Number validators."""

from typing import Any, Dict, List
from api_testing.constraint.ir.models import ViolationModel


def number_range_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate numbers are within [min, max] range."""
    violations = []
    min_val = args.get("min")
    max_val = args.get("max")

    for value in values:
        # Accept int and float, but not bool
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="number.range@v1",
                    message=f"Expected number, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if min_val is not None and value < min_val:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="number.range@v1",
                    message=f"Value {value} is less than minimum {min_val}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_val, "max": max_val},
                )
            )

        if max_val is not None and value > max_val:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="number.range@v1",
                    message=f"Value {value} exceeds maximum {max_val}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_val, "max": max_val},
                )
            )

    return violations


def number_positive_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate numbers are positive (> 0)."""
    violations = []

    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="number.positive@v1",
                    message=f"Expected number, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if value <= 0:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="number.positive@v1",
                    message=f"Value {value} is not positive",
                    path=ctx.get("path", ""),
                    value=value,
                    expected="positive number (> 0)",
                )
            )

    return violations


__all__ = ["number_range_v1", "number_positive_v1"]
