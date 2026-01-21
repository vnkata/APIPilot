"""Integer validators."""

from typing import Any, Dict, List
from api_testing.constraint.ir.models import ViolationModel


def int_range_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate integers are within [min, max] range."""
    violations = []
    min_val = args.get("min")
    max_val = args.get("max")

    for value in values:
        # Type check
        if not isinstance(value, int) or isinstance(value, bool):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="int.range@v1",
                    message=f"Expected integer, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if min_val is not None and value < min_val:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="int.range@v1",
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
                    predicate_ref="int.range@v1",
                    message=f"Value {value} exceeds maximum {max_val}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_val, "max": max_val},
                )
            )

    return violations


def int_enum_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate integers are in allowed enum values."""
    violations = []
    allowed = set(args.get("values", []))

    for value in values:
        # Type check
        if not isinstance(value, int) or isinstance(value, bool):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="int.enum@v1",
                    message=f"Expected integer, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if value not in allowed:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="int.enum@v1",
                    message=f"Value {value} not in allowed values {sorted(allowed)}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"values": sorted(allowed)},
                )
            )

    return violations


def int_positive_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate integers are positive (> 0)."""
    violations = []

    for value in values:
        if not isinstance(value, int) or isinstance(value, bool):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="int.positive@v1",
                    message=f"Expected integer, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if value <= 0:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="int.positive@v1",
                    message=f"Value {value} is not positive",
                    path=ctx.get("path", ""),
                    value=value,
                    expected="positive integer (> 0)",
                )
            )

    return violations


__all__ = ["int_range_v1", "int_enum_v1", "int_positive_v1"]
