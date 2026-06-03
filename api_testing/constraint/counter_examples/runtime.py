"""Runtime helpers for approved counter-example cases."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from api_testing.models.http_data import RequestData, ResponseData

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


def counter_example_request_to_request_data(request: Mapping[str, Any]) -> RequestData:
    """Convert planner request shape into executable APIPilot request data."""
    method = str(request.get("method") or request.get("http_method") or "GET").upper()
    path = str(request.get("path") or request.get("endpoint_path") or "/")
    path_parameters = dict(request.get("path_parameters") or {})
    query = dict(request.get("query") or request.get("parameters") or {})
    headers = dict(request.get("headers") or {})
    body = request.get("body")

    endpoint_path = path
    for key, value in path_parameters.items():
        endpoint_path = endpoint_path.replace(f"{{{key}}}", str(value))
    unresolved = re.findall(r"{([^}]+)}", endpoint_path)
    if unresolved:
        raise ValueError(
            "unresolved path parameter(s): " + ", ".join(sorted(set(unresolved)))
        )

    return RequestData(
        endpoint_path=endpoint_path,
        http_method=method,
        parameters=query,
        headers=headers,
        body=body,
        mime_type=str(request.get("mime_type") or "application/json"),
        expected_code="2xx",
    )


def evaluate_counter_example_runtime_case(
    *,
    run_name: str,
    detail: Any,
    request: RequestData,
    response: ResponseData,
    index: int,
    cache_root: Path,
) -> dict[str, Any]:
    """Evaluate a response against static/dynamic constraints and sanitize output."""
    from api_testing.constraint.conflict_resolver import (
        ConstraintConflictResolver,
        ConstraintRuleEvaluator,
    )

    resolver = ConstraintConflictResolver(
        cache_dir=cache_root / run_name,
        evaluator=ConstraintRuleEvaluator(),
    )
    record = {
        "endpoint": detail.operation_id,
        "property": detail.property_path,
        "static_constraint": detail.static_constraint,
        "dynamic_constraint": detail.dynamic_constraint,
    }
    result = resolver.evaluate_case(record, request, response, index)
    return _sanitize(result)


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    normalized = lowered.replace("-", "_")
    return any(part in lowered or part in normalized for part in SENSITIVE_KEY_PARTS)


def _sanitize(value: Any) -> Any:
    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            sanitized[key_text] = "<REDACTED>" if _is_sensitive_key(key_text) else _sanitize(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, str) and value.strip().lower().startswith(SENSITIVE_VALUE_PREFIXES):
        return "<REDACTED>"
    return value
