"""Boolean validators."""

from typing import Any, Dict, List
from api_testing.constraint.ir.models import ViolationModel


def boolean_const_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate booleans have specific constant value."""
    violations = []
    expected_value = args.get("value")

    for value in values:
        if not isinstance(value, bool):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="boolean.const@v1",
                    message=f"Expected boolean, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if value != expected_value:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="boolean.const@v1",
                    message=f"Value {value} does not match expected {expected_value}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected=expected_value,
                )
            )

    return violations


__all__ = ["boolean_const_v1"]
