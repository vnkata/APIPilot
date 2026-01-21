"""Comparison validators for cross-field and request-response constraints."""

from typing import Any, Dict, List
from api_testing.constraint.ir.models import ViolationModel


def comparison_less_than_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate first value < second value.

    Args:
        values: List of [value_a, value_b] pairs or single values to compare with threshold
        args: {"threshold": value} for single value comparison, or empty for pair comparison
        ctx: Validation context
    """
    violations = []
    threshold = args.get("threshold")

    for value in values:
        if threshold is not None:
            # Single value comparison with threshold
            try:
                if not (value < threshold):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.less_than@v1",
                            message=f"Value {value} is not less than {threshold}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"threshold": threshold, "operator": "<"},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.less_than@v1",
                        message=f"Cannot compare {value} < {threshold}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
        else:
            # Pair comparison: expect value to be [a, b]
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.less_than@v1",
                        message=f"Expected [value_a, value_b] pair, got {value}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
                continue

            value_a, value_b = value
            try:
                if not (value_a < value_b):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.less_than@v1",
                            message=f"{value_a} is not less than {value_b}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"operator": "<"},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.less_than@v1",
                        message=f"Cannot compare {value_a} < {value_b}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )

    return violations


def comparison_less_than_or_equal_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate first value <= second value."""
    violations = []
    threshold = args.get("threshold")

    for value in values:
        if threshold is not None:
            try:
                if not (value <= threshold):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.less_than_or_equal@v1",
                            message=f"Value {value} is not less than or equal to {threshold}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"threshold": threshold, "operator": "<="},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.less_than_or_equal@v1",
                        message=f"Cannot compare {value} <= {threshold}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
        else:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.less_than_or_equal@v1",
                        message=f"Expected [value_a, value_b] pair, got {value}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
                continue

            value_a, value_b = value
            try:
                if not (value_a <= value_b):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.less_than_or_equal@v1",
                            message=f"{value_a} is not less than or equal to {value_b}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"operator": "<="},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.less_than_or_equal@v1",
                        message=f"Cannot compare {value_a} <= {value_b}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )

    return violations


def comparison_greater_than_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate first value > second value."""
    violations = []
    threshold = args.get("threshold")

    for value in values:
        if threshold is not None:
            try:
                if not (value > threshold):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.greater_than@v1",
                            message=f"Value {value} is not greater than {threshold}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"threshold": threshold, "operator": ">"},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.greater_than@v1",
                        message=f"Cannot compare {value} > {threshold}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
        else:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.greater_than@v1",
                        message=f"Expected [value_a, value_b] pair, got {value}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
                continue

            value_a, value_b = value
            try:
                if not (value_a > value_b):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.greater_than@v1",
                            message=f"{value_a} is not greater than {value_b}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"operator": ">"},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.greater_than@v1",
                        message=f"Cannot compare {value_a} > {value_b}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )

    return violations


def comparison_greater_than_or_equal_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate first value >= second value."""
    violations = []
    threshold = args.get("threshold")

    for value in values:
        if threshold is not None:
            try:
                if not (value >= threshold):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.greater_than_or_equal@v1",
                            message=f"Value {value} is not greater than or equal to {threshold}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"threshold": threshold, "operator": ">="},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.greater_than_or_equal@v1",
                        message=f"Cannot compare {value} >= {threshold}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
        else:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.greater_than_or_equal@v1",
                        message=f"Expected [value_a, value_b] pair, got {value}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
                continue

            value_a, value_b = value
            try:
                if not (value_a >= value_b):
                    violations.append(
                        ViolationModel(
                            constraint_id=ctx.get("constraint_id", "unknown"),
                            predicate_ref="comparison.greater_than_or_equal@v1",
                            message=f"{value_a} is not greater than or equal to {value_b}",
                            path=ctx.get("path", ""),
                            value=value,
                            expected={"operator": ">="},
                        )
                    )
            except TypeError as e:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.greater_than_or_equal@v1",
                        message=f"Cannot compare {value_a} >= {value_b}: {str(e)}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )

    return violations


def comparison_equals_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate values are equal."""
    violations = []
    expected = args.get("expected")

    for value in values:
        if expected is not None:
            if value != expected:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.equals@v1",
                        message=f"Value {value} does not equal expected {expected}",
                        path=ctx.get("path", ""),
                        value=value,
                        expected={"expected": expected},
                    )
                )
        else:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.equals@v1",
                        message=f"Expected [value_a, value_b] pair, got {value}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
                continue

            value_a, value_b = value
            if value_a != value_b:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.equals@v1",
                        message=f"{value_a} does not equal {value_b}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )

    return violations


def comparison_not_equals_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate values are not equal."""
    violations = []
    forbidden = args.get("forbidden")

    for value in values:
        if forbidden is not None:
            if value == forbidden:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.not_equals@v1",
                        message=f"Value {value} equals forbidden value {forbidden}",
                        path=ctx.get("path", ""),
                        value=value,
                        expected={"forbidden": forbidden},
                    )
                )
        else:
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.not_equals@v1",
                        message=f"Expected [value_a, value_b] pair, got {value}",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )
                continue

            value_a, value_b = value
            if value_a == value_b:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.not_equals@v1",
                        message=f"{value_a} equals {value_b} but should not",
                        path=ctx.get("path", ""),
                        value=value,
                    )
                )

    return violations


def comparison_between_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate value is between min and max (inclusive)."""
    violations = []
    min_val = args.get("min")
    max_val = args.get("max")

    if min_val is None or max_val is None:
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="comparison.between@v1",
                    message="Both min and max must be specified for between constraint",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
        return violations

    for value in values:
        try:
            if not (min_val <= value <= max_val):
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="comparison.between@v1",
                        message=f"Value {value} is not between {min_val} and {max_val}",
                        path=ctx.get("path", ""),
                        value=value,
                        expected={"min": min_val, "max": max_val},
                    )
                )
        except TypeError as e:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="comparison.between@v1",
                    message=f"Cannot check if {value} is between {min_val} and {max_val}: {str(e)}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )

    return violations


__all__ = [
    "comparison_less_than_v1",
    "comparison_less_than_or_equal_v1",
    "comparison_greater_than_v1",
    "comparison_greater_than_or_equal_v1",
    "comparison_equals_v1",
    "comparison_not_equals_v1",
    "comparison_between_v1",
]
