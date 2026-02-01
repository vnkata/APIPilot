"""Array validators."""

from typing import Any

from api_testing.constraint.ir.core import ViolationModel


def array_length_v1(
    values: list[Any], args: dict[str, Any], ctx: dict
) -> list[ViolationModel]:
    """Validate array length is within [min, max]."""
    violations = []
    min_len = args.get("min")
    max_len = args.get("max")

    for value in values:
        if not isinstance(value, list):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="array.length@v1",
                    message=f"Expected array, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        length = len(value)

        if min_len is not None and length < min_len:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="array.length@v1",
                    message=f"Array length {length} is less than minimum {min_len}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_len, "max": max_len},
                )
            )

        if max_len is not None and length > max_len:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="array.length@v1",
                    message=f"Array length {length} exceeds maximum {max_len}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_len, "max": max_len},
                )
            )

    return violations


def array_unique_v1(
    values: list[Any], args: dict[str, Any], ctx: dict
) -> list[ViolationModel]:
    """Validate array contains only unique items."""
    violations = []

    for value in values:
        if not isinstance(value, list):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="array.unique@v1",
                    message=f"Expected array, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        # Check for duplicates
        seen = set()
        duplicates = []
        for item in value:
            # Convert unhashable types to strings for comparison
            try:
                key = (
                    item
                    if isinstance(item, (str, int, float, bool, type(None)))
                    else str(item)
                )
                if key in seen:
                    duplicates.append(item)
                seen.add(key)
            except:
                pass

        if duplicates:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="array.unique@v1",
                    message=f"Array contains duplicate items: {duplicates[:5]}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )

    return violations


__all__ = ["array_length_v1", "array_unique_v1"]
