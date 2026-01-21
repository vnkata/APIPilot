"""Request-response validators for complex validation patterns."""

from typing import Any, Dict, List
from datetime import datetime
from api_testing.constraint.ir.models import ViolationModel


def forall_eq_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate all items in array equal a specific value.

    Args:
        values: List containing the array to validate
        args: {"expected": value to match} or extracted from context
        ctx: Validation context with expected value
    """
    violations = []
    expected = args.get("expected")

    for value in values:
        if not isinstance(value, list):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="forall_eq@v1",
                    message=f"Expected array, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        for idx, item in enumerate(value):
            if item != expected:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="forall_eq@v1",
                        message=f"Item at index {idx} ({item}) does not equal expected value {expected}",
                        path=f"{ctx.get('path', '')}[{idx}]",
                        value=item,
                        expected={"expected": expected},
                    )
                )

    return violations


def exists_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate at least one item in array matches condition.

    Args:
        values: List containing the array to validate
        args: {"predicate": predicate_ref, "args": predicate args} or {"match": value}
        ctx: Validation context
    """
    violations = []
    match_value = args.get("match")

    for value in values:
        if not isinstance(value, list):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="exists@v1",
                    message=f"Expected array, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if match_value is not None:
            # Simple value matching
            if match_value not in value:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="exists@v1",
                        message=f"No item in array matches value {match_value}",
                        path=ctx.get("path", ""),
                        value=value,
                        expected={"match": match_value},
                    )
                )

    return violations


def len_le_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate array length is less than or equal to max."""
    violations = []
    max_len = args.get("max")

    if max_len is None:
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_le@v1",
                    message="max parameter is required for len_le constraint",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
        return violations

    for value in values:
        if not isinstance(value, (list, tuple, str)):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_le@v1",
                    message=f"Expected array/string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        length = len(value)
        if length > max_len:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_le@v1",
                    message=f"Length {length} exceeds maximum {max_len}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"max": max_len},
                )
            )

    return violations


def len_eq_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate array length equals expected."""
    violations = []
    expected_len = args.get("expected")

    if expected_len is None:
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_eq@v1",
                    message="expected parameter is required for len_eq constraint",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
        return violations

    for value in values:
        if not isinstance(value, (list, tuple, str)):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_eq@v1",
                    message=f"Expected array/string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        length = len(value)
        if length != expected_len:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_eq@v1",
                    message=f"Length {length} does not equal expected {expected_len}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"expected": expected_len},
                )
            )

    return violations


def len_ge_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate array length is greater than or equal to min."""
    violations = []
    min_len = args.get("min")

    if min_len is None:
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_ge@v1",
                    message="min parameter is required for len_ge constraint",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
        return violations

    for value in values:
        if not isinstance(value, (list, tuple, str)):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_ge@v1",
                    message=f"Expected array/string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        length = len(value)
        if length < min_len:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="len_ge@v1",
                    message=f"Length {length} is less than minimum {min_len}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_len},
                )
            )

    return violations


def sorted_by_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate array is sorted by a specific field.

    Args:
        values: List containing arrays to validate
        args: {"key": field_name, "direction": "asc"|"desc", "type": "numeric"|"string"|"date"}
        ctx: Validation context
    """
    violations = []
    key = args.get("key")
    direction = args.get("direction", "asc")
    sort_type = args.get("type", "numeric")

    for value in values:
        if not isinstance(value, list):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="sorted_by@v1",
                    message=f"Expected array, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if len(value) < 2:
            continue  # Array of 0 or 1 item is always sorted

        # Extract values to compare
        compare_values = []
        for item in value:
            if isinstance(item, dict) and key:
                compare_values.append(item.get(key))
            else:
                compare_values.append(item)

        # Check if sorted
        is_sorted = True
        for i in range(len(compare_values) - 1):
            curr, next_val = compare_values[i], compare_values[i + 1]

            # Skip None values
            if curr is None or next_val is None:
                continue

            try:
                if direction == "asc":
                    if curr > next_val:
                        is_sorted = False
                        break
                else:  # desc
                    if curr < next_val:
                        is_sorted = False
                        break
            except TypeError:
                # Can't compare, assume not sorted
                is_sorted = False
                break

        if not is_sorted:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="sorted_by@v1",
                    message=f"Array is not sorted by {key} in {direction} order",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"key": key, "direction": direction, "type": sort_type},
                )
            )

    return violations


def implies_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate conditional constraint: if condition is true, then consequent must be true.

    Args:
        values: List of [condition_result, consequent_result] pairs
        args: Not used, logic is in the value pairs
        ctx: Validation context
    """
    violations = []

    for value in values:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="implies@v1",
                    message=f"Expected [condition, consequent] pair, got {value}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        condition, consequent = value

        # If condition is true, consequent must also be true
        if condition and not consequent:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="implies@v1",
                    message=f"Condition is true but consequent is false",
                    path=ctx.get("path", ""),
                    value=value,
                    expected="If condition then consequent",
                )
            )

    return violations


def contains_substring_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate string contains substring.

    Args:
        values: Strings to validate
        args: {"substring": str, "case_sensitive": bool}
        ctx: Validation context
    """
    violations = []
    substring = args.get("substring")
    case_sensitive = args.get("case_sensitive", True)

    if substring is None:
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="contains_substring@v1",
                    message="substring parameter is required",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
        return violations

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="contains_substring@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        check_value = value if case_sensitive else value.lower()
        check_substring = substring if case_sensitive else substring.lower()

        if check_substring not in check_value:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="contains_substring@v1",
                    message=f"String '{value}' does not contain substring '{substring}'",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"substring": substring, "case_sensitive": case_sensitive},
                )
            )

    return violations


def date_in_range_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate date is within range [start_date, end_date].

    Args:
        values: Date strings to validate (ISO format)
        args: {"start_date": str, "end_date": str}
        ctx: Validation context
    """
    violations = []
    start_date = args.get("start_date")
    end_date = args.get("end_date")

    if start_date is None or end_date is None:
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date_in_range@v1",
                    message="Both start_date and end_date are required",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
        return violations

    # Parse date bounds
    try:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date_in_range@v1",
                    message=f"Invalid date range parameters: {str(e)}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
        return violations

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date_in_range@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        try:
            value_dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date_in_range@v1",
                    message=f"Invalid date format '{value}': {str(e)}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if not (start_dt <= value_dt <= end_dt):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="date_in_range@v1",
                    message=f"Date {value} is not within range [{start_date}, {end_date}]",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"start_date": start_date, "end_date": end_date},
                )
            )

    return violations


def field_exists_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate field exists in object.

    Args:
        values: Objects to check
        args: {"field": field_name} or use context path
        ctx: Validation context
    """
    violations = []
    field_name = args.get("field")

    # If values is empty list, field doesn't exist
    if not values:
        violations.append(
            ViolationModel(
                constraint_id=ctx.get("constraint_id", "unknown"),
                predicate_ref="field_exists@v1",
                message=f"Field {field_name or ctx.get('path', 'unknown')} does not exist",
                path=ctx.get("path", ""),
                value=None,
                expected={"field": field_name},
            )
        )

    return violations


def field_absent_v1(
    values: List[Any], args: Dict[str, Any], ctx: Dict
) -> List[ViolationModel]:
    """Validate field does not exist in object.

    Args:
        values: Objects to check
        args: {"field": field_name} or use context path
        ctx: Validation context
    """
    violations = []
    field_name = args.get("field")

    # If values has items, field exists (should be absent)
    if values:
        violations.append(
            ViolationModel(
                constraint_id=ctx.get("constraint_id", "unknown"),
                predicate_ref="field_absent@v1",
                message=f"Field {field_name or ctx.get('path', 'unknown')} should not exist but does",
                path=ctx.get("path", ""),
                value=values[0] if values else None,
                expected={"field": field_name, "should_exist": False},
            )
        )

    return violations


__all__ = [
    "forall_eq_v1",
    "exists_v1",
    "len_le_v1",
    "len_eq_v1",
    "len_ge_v1",
    "sorted_by_v1",
    "implies_v1",
    "contains_substring_v1",
    "date_in_range_v1",
    "field_exists_v1",
    "field_absent_v1",
]
