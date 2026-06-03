"""Build bounded counter-example generation context from combination rows."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

SENSITIVE_KEY_PARTS = (
    "authorization",
    "token",
    "api_key",
    "api-key",
    "apikey",
    "secret",
    "password",
    "credential",
    "cookie",
)
SENSITIVE_VALUE_PREFIXES = ("bearer ", "basic ")


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    normalized = lowered.replace("-", "_")
    return any(part in lowered or part in normalized for part in SENSITIVE_KEY_PARTS)


def _sanitize(value: Any, *, max_text_length: int) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _is_sensitive_key(key_text):
                sanitized[key_text] = "<REDACTED>"
            else:
                sanitized[key_text] = _sanitize(item, max_text_length=max_text_length)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item, max_text_length=max_text_length) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item, max_text_length=max_text_length) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lower().startswith(SENSITIVE_VALUE_PREFIXES):
            return "<REDACTED>"
        if len(stripped) > max_text_length:
            return stripped[: max_text_length - 3] + "..."
        return stripped
    return value


def _bounded_items(items: Any, *, max_items: int, max_text_length: int) -> list[Any]:
    if items is None:
        return []
    if isinstance(items, Mapping):
        iterable: Sequence[Any] = [items]
    elif isinstance(items, Sequence) and not isinstance(items, str):
        iterable = items
    else:
        iterable = [items]
    return [
        _sanitize(item, max_text_length=max_text_length)
        for item in list(iterable)[:max_items]
    ]


def _endpoint_parts(combination: Mapping[str, Any]) -> tuple[str | None, str | None]:
    method = combination.get("method")
    path = combination.get("path")
    endpoint = str(combination.get("operation_id") or combination.get("endpoint") or "")
    if not method and "-" in endpoint:
        maybe_method, maybe_path = endpoint.split("-", 1)
        method = maybe_method
        path = path or maybe_path
    return (
        str(method).lower() if method else None,
        str(path) if path else None,
    )


def _operation_summary(
    combination: Mapping[str, Any],
    openapi_spec: Mapping[str, Any] | None,
    *,
    max_text_length: int,
) -> dict[str, Any]:
    method, path = _endpoint_parts(combination)
    summary: dict[str, Any] = {"method": method, "path": path}
    if not openapi_spec or not method or not path:
        return summary

    operation = (
        openapi_spec.get("paths", {})
        .get(path, {})
        .get(method.lower(), {})
    )
    if not isinstance(operation, Mapping):
        return summary

    request_schema: Any | None = None
    request_body = operation.get("requestBody")
    if isinstance(request_body, Mapping):
        content = request_body.get("content")
        if isinstance(content, Mapping):
            for content_item in content.values():
                if isinstance(content_item, Mapping) and "schema" in content_item:
                    request_schema = content_item["schema"]
                    break

    summary.update(
        {
            "operation_id": operation.get("operationId"),
            "parameters": _sanitize(
                list(operation.get("parameters") or []),
                max_text_length=max_text_length,
            ),
            "request_schema": _sanitize(
                request_schema,
                max_text_length=max_text_length,
            ),
        }
    )
    return summary


def build_counter_example_context(
    combination: Mapping[str, Any],
    *,
    openapi_spec: Mapping[str, Any] | None = None,
    reports: Any = None,
    test_cases: Any = None,
    contextual_memory: Any = None,
    max_items: int = 5,
    max_text_length: int = 500,
) -> dict[str, Any]:
    sanitized_combination = _sanitize(
        dict(combination),
        max_text_length=max_text_length,
    )
    return {
        "case_id": combination.get("case_id"),
        "operation_id": sanitized_combination.get("operation_id")
        or sanitized_combination.get("endpoint"),
        "property_path": sanitized_combination.get("property_path")
        or sanitized_combination.get("property"),
        "relation": sanitized_combination.get("relation"),
        "status": sanitized_combination.get("status"),
        "static_constraint": sanitized_combination.get("static_constraint"),
        "dynamic_constraint": sanitized_combination.get("dynamic_constraint"),
        "final_constraint": sanitized_combination.get("final_constraint"),
        "reason": sanitized_combination.get("reason")
        or sanitized_combination.get("reason_preview"),
        "counter_example": sanitized_combination.get("counter_example"),
        "expected_target_truth_vector": sanitized_combination.get(
            "expected_target_truth_vector"
        ),
        "operation": _operation_summary(
            combination,
            openapi_spec,
            max_text_length=max_text_length,
        ),
        "reports_summary": _bounded_items(
            reports,
            max_items=max_items,
            max_text_length=max_text_length,
        ),
        "test_cases_summary": _bounded_items(
            test_cases,
            max_items=max_items,
            max_text_length=max_text_length,
        ),
        "contextual_memory_summary": _bounded_items(
            contextual_memory,
            max_items=max_items,
            max_text_length=max_text_length,
        ),
    }
