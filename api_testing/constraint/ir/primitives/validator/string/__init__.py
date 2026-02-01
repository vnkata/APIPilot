"""String validators."""

import re
from typing import Any, Dict, List

from api_testing.constraint.ir.core import ViolationModel


def string_enum_v1(
    values: list[Any], args: dict[str, Any], ctx: dict
) -> list[ViolationModel]:
    """Validate strings are in allowed enum values."""
    violations = []
    allowed = set(args.get("values", []))

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.enum@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if value not in allowed:
            display_values = sorted(allowed)[:10]
            if len(allowed) > 10:
                display_values.append("...")
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.enum@v1",
                    message=f"Value '{value}' not in allowed values {display_values}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"values": sorted(allowed)},
                )
            )

    return violations


def string_pattern_v1(
    values: list[Any], args: dict[str, Any], ctx: dict
) -> list[ViolationModel]:
    """Validate strings match regex pattern."""
    violations = []
    pattern = args.get("pattern", "")

    try:
        regex = re.compile(pattern)
    except re.error as e:
        # Invalid pattern - fail all
        for value in values:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.pattern@v1",
                    message=f"Invalid regex pattern: {str(e)}",
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
                    predicate_ref="string.pattern@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if not regex.match(value):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.pattern@v1",
                    message=f"Value '{value}' does not match pattern '{pattern}'",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"pattern": pattern},
                )
            )

    return violations


def string_length_v1(
    values: list[Any], args: dict[str, Any], ctx: dict
) -> list[ViolationModel]:
    """Validate string length is within [min, max]."""
    violations = []
    min_len = args.get("min")
    max_len = args.get("max")

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.length@v1",
                    message=f"Expected string, got {type(value).__name__}",
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
                    predicate_ref="string.length@v1",
                    message=f"String length {length} is less than minimum {min_len}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_len, "max": max_len},
                )
            )

        if max_len is not None and length > max_len:
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.length@v1",
                    message=f"String length {length} exceeds maximum {max_len}",
                    path=ctx.get("path", ""),
                    value=value,
                    expected={"min": min_len, "max": max_len},
                )
            )

    return violations


def string_uri_v1(
    values: list[Any], args: dict[str, Any], ctx: dict
) -> list[ViolationModel]:
    """Validate strings are valid URIs with optional scheme restriction."""
    violations = []
    allowed_schemes = args.get("allowed_schemes", [])

    # Simple URI pattern
    uri_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://[^\s]+$")

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.uri@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if not uri_pattern.match(value):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.uri@v1",
                    message=f"Value '{value}' is not a valid URI",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if allowed_schemes:
            scheme = value.split("://")[0].lower()
            if scheme not in allowed_schemes:
                violations.append(
                    ViolationModel(
                        constraint_id=ctx.get("constraint_id", "unknown"),
                        predicate_ref="string.uri@v1",
                        message=f"URI scheme '{scheme}' not in allowed schemes {allowed_schemes}",
                        path=ctx.get("path", ""),
                        value=value,
                        expected={"allowed_schemes": allowed_schemes},
                    )
                )

    return violations


def string_email_v1(
    values: list[Any], args: dict[str, Any], ctx: dict
) -> list[ViolationModel]:
    """Validate strings are valid email addresses."""
    violations = []

    # Simple email pattern
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    for value in values:
        if not isinstance(value, str):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.email@v1",
                    message=f"Expected string, got {type(value).__name__}",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )
            continue

        if not email_pattern.match(value):
            violations.append(
                ViolationModel(
                    constraint_id=ctx.get("constraint_id", "unknown"),
                    predicate_ref="string.email@v1",
                    message=f"Value '{value}' is not a valid email address",
                    path=ctx.get("path", ""),
                    value=value,
                )
            )

    return violations


__all__ = [
    "string_enum_v1",
    "string_pattern_v1",
    "string_length_v1",
    "string_uri_v1",
    "string_email_v1",
]
