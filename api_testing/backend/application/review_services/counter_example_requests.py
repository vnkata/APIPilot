from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping

from pydantic import JsonValue

from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.redaction import REDACTED_VALUE, is_sensitive_key


REDACTED_SECRET_REF = {"type": "redacted", "reason": "sensitive_header"}
SECRET_REF_TYPES = {"env"}


@dataclass(frozen=True, slots=True)
class RequestAllowlist:
    query: set[str]
    body: set[str]


@dataclass(frozen=True, slots=True)
class PreparedCounterExampleRequest:
    request_private: dict[str, JsonValue]
    request_display: dict[str, JsonValue]
    validation_error: dict[str, JsonValue] | None


def allowlist_from_spec(
    specification: JsonValue | None,
    operation_id: str,
) -> RequestAllowlist:
    query: set[str] = set()
    body: set[str] = set()
    if not isinstance(specification, Mapping):
        return RequestAllowlist(query=query, body=body)

    operation = _operation_from_spec(specification, operation_id)
    if not isinstance(operation, Mapping):
        return RequestAllowlist(query=query, body=body)

    parameters = operation.get("parameters")
    if isinstance(parameters, Mapping):
        for name, parameter in parameters.items():
            if isinstance(parameter, Mapping):
                location = str(parameter.get("in") or parameter.get("in_value") or "")
            else:
                location = ""
            if location.lower() == "query":
                query.add(str(name))
    elif isinstance(parameters, list):
        for parameter in parameters:
            if not isinstance(parameter, Mapping):
                continue
            if str(parameter.get("in") or parameter.get("in_value") or "").lower() == "query":
                name = parameter.get("name")
                if name is not None:
                    query.add(str(name))

    body.update(_request_body_properties(operation.get("requestBody")))
    body.update(_request_body_properties(operation.get("request_body")))
    return RequestAllowlist(query=query, body=body)


def prepare_counter_example_request(
    request: JsonValue | None,
    *,
    allowlist: RequestAllowlist,
) -> PreparedCounterExampleRequest:
    normalized = normalize_counter_example_request(request)
    raw_secret_paths: list[str] = []
    private_headers, display_headers = _prepare_secret_container(
        normalized.get("headers"),
        path_prefix="headers",
        raw_secret_paths=raw_secret_paths,
    )
    private_cookies, display_cookies = _prepare_secret_container(
        normalized.get("cookies"),
        path_prefix="cookies",
        raw_secret_paths=raw_secret_paths,
    )
    private_body, display_body = _prepare_body(
        normalized.get("body"),
        allowlist=allowlist.body,
        path_prefix="body",
        raw_secret_paths=raw_secret_paths,
    )
    private_query, display_query = _prepare_query(
        normalized.get("query"),
        allowlist=allowlist.query,
    )

    request_private: dict[str, JsonValue] = {
        "method": normalized["method"],
        "path": normalized["path"],
        "path_parameters": normalized["path_parameters"],
        "query": private_query,
        "headers": private_headers,
    }
    request_display: dict[str, JsonValue] = {
        "method": normalized["method"],
        "path": normalized["path"],
        "path_parameters": normalized["path_parameters"],
        "query": display_query,
        "headers": display_headers,
    }
    if private_cookies:
        request_private["cookies"] = private_cookies
        request_display["cookies"] = display_cookies
    if "body" in normalized:
        request_private["body"] = private_body
        request_display["body"] = display_body
    if normalized.get("mime_type"):
        request_private["mime_type"] = normalized["mime_type"]
        request_display["mime_type"] = normalized["mime_type"]

    validation_error: dict[str, JsonValue] | None = None
    if raw_secret_paths:
        validation_error = {
            "raw_secret_values": [
                {
                    "path": path,
                    "message": "Raw sensitive value was replaced with a non-executable redacted marker.",
                }
                for path in sorted(raw_secret_paths)
            ]
        }
    return PreparedCounterExampleRequest(
        request_private=request_private,
        request_display=request_display,
        validation_error=validation_error,
    )


def normalize_counter_example_request(request: JsonValue | None) -> dict[str, JsonValue]:
    if not isinstance(request, Mapping):
        request = {}
    method = str(request.get("method") or request.get("http_method") or "GET").upper()
    path = str(request.get("path") or request.get("endpoint_path") or "/")
    normalized: dict[str, JsonValue] = {
        "method": method,
        "path": path,
        "path_parameters": _dict_or_empty(request.get("path_parameters")),
        "query": _dict_or_empty(request.get("query") or request.get("parameters")),
        "headers": _dict_or_empty(request.get("headers")),
    }
    cookies = _dict_or_empty(request.get("cookies"))
    if cookies:
        normalized["cookies"] = cookies
    if "body" in request:
        normalized["body"] = request.get("body")
    if request.get("mime_type"):
        normalized["mime_type"] = str(request.get("mime_type"))
    return normalized


def assert_executable_request_safe(request: JsonValue | None) -> None:
    if _contains_redacted_literal(request):
        raise InvalidArtifactRequest(
            "counter-example execution rejected: redacted executable request value is not executable"
        )
    redacted_ref = _find_redacted_ref(request)
    if redacted_ref is not None:
        raise InvalidArtifactRequest(
            f"counter-example execution rejected: redacted executable request value at {redacted_ref}"
        )


def resolve_secret_refs(request: JsonValue | None) -> JsonValue | None:
    return _resolve_secret_refs(request, path="$")


def has_redacted_literal(value: JsonValue | None) -> bool:
    return _contains_redacted_literal(value)


def merge_validation_errors(
    current: JsonValue | None,
    extra: JsonValue | None,
) -> JsonValue | None:
    if current is None:
        return extra
    if extra is None:
        return current
    merged: dict[str, JsonValue] = {}
    if isinstance(current, Mapping):
        merged.update({str(key): item for key, item in current.items()})
    else:
        merged["previous"] = current
    if isinstance(extra, Mapping):
        for key, value in extra.items():
            if key in merged and isinstance(merged[key], list) and isinstance(value, list):
                merged[key] = [*merged[key], *value]
            else:
                merged[str(key)] = value
    else:
        merged["extra"] = extra
    return merged


def redacted_executable_validation_error() -> dict[str, bool]:
    return {"redacted_executable_request": True}


def _operation_from_spec(
    specification: Mapping[str, Any],
    operation_id: str,
) -> Mapping[str, Any] | None:
    operations = specification.get("operations")
    if isinstance(operations, Mapping) and isinstance(operations.get(operation_id), Mapping):
        return operations[operation_id]
    method, _, path = operation_id.partition("-")
    if method and path:
        operation = specification.get("paths", {}).get(path, {}).get(method.lower())
        if isinstance(operation, Mapping):
            return operation
    return None


def _request_body_properties(request_body: Any) -> set[str]:
    properties: set[str] = set()
    if not isinstance(request_body, Mapping):
        return properties
    schema = request_body.get("schema")
    content = request_body.get("content")
    if isinstance(content, Mapping):
        for media in content.values():
            if isinstance(media, Mapping) and isinstance(media.get("schema"), Mapping):
                schema = media["schema"]
                break
    if isinstance(schema, Mapping):
        raw_properties = schema.get("properties")
        if isinstance(raw_properties, Mapping):
            properties.update(str(name) for name in raw_properties)
    raw_properties = request_body.get("properties")
    if isinstance(raw_properties, Mapping):
        properties.update(str(name) for name in raw_properties)
    return properties


def _prepare_secret_container(
    value: JsonValue | None,
    *,
    path_prefix: str,
    raw_secret_paths: list[str],
) -> tuple[dict[str, JsonValue], dict[str, JsonValue]]:
    private: dict[str, JsonValue] = {}
    display: dict[str, JsonValue] = {}
    for key, item in _dict_or_empty(value).items():
        key_text = str(key)
        path = f"{path_prefix}.{key_text}"
        if is_sensitive_key(key_text):
            if _is_typed_secret_ref(item):
                private[key_text] = item
            else:
                private[key_text] = dict(REDACTED_SECRET_REF)
                raw_secret_paths.append(path)
            display[key_text] = REDACTED_VALUE
            continue
        private[key_text] = item
        display[key_text] = _display_sanitize(item, path=path, allowlisted=False)
    return private, display


def _prepare_query(
    value: JsonValue | None,
    *,
    allowlist: set[str],
) -> tuple[dict[str, JsonValue], dict[str, JsonValue]]:
    private: dict[str, JsonValue] = {}
    display: dict[str, JsonValue] = {}
    for key, item in _dict_or_empty(value).items():
        key_text = str(key)
        private[key_text] = item
        display[key_text] = _display_sanitize(
            item,
            path=f"query.{key_text}",
            allowlisted=key_text in allowlist or not is_sensitive_key(key_text),
        )
    return private, display


def _prepare_body(
    value: JsonValue | None,
    *,
    allowlist: set[str],
    path_prefix: str,
    raw_secret_paths: list[str],
) -> tuple[JsonValue | None, JsonValue | None]:
    if isinstance(value, Mapping):
        private: dict[str, JsonValue] = {}
        display: dict[str, JsonValue] = {}
        for key, item in value.items():
            key_text = str(key)
            key_path = f"{path_prefix}.{key_text}"
            allowlisted = key_text in allowlist
            if is_sensitive_key(key_text) and not allowlisted:
                private[key_text] = dict(REDACTED_SECRET_REF)
                display[key_text] = REDACTED_VALUE
                raw_secret_paths.append(key_path)
                continue
            child_private, child_display = _prepare_body(
                item,
                allowlist=set(),
                path_prefix=key_path,
                raw_secret_paths=raw_secret_paths,
            )
            private[key_text] = child_private
            display[key_text] = (
                child_display
                if allowlisted
                else _display_sanitize(child_display, path=key_path, allowlisted=False)
            )
        return private, display
    if isinstance(value, list):
        private_items: list[JsonValue] = []
        display_items: list[JsonValue] = []
        for index, item in enumerate(value):
            item_private, item_display = _prepare_body(
                item,
                allowlist=set(),
                path_prefix=f"{path_prefix}[{index}]",
                raw_secret_paths=raw_secret_paths,
            )
            private_items.append(item_private)
            display_items.append(item_display)
        return private_items, display_items
    return value, value


def _display_sanitize(
    value: JsonValue | None,
    *,
    path: str,
    allowlisted: bool,
) -> JsonValue | None:
    if allowlisted:
        return value
    if _is_typed_secret_ref(value):
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return {
            str(key): (
                REDACTED_VALUE
                if is_sensitive_key(str(key))
                else _display_sanitize(item, path=f"{path}.{key}", allowlisted=False)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _display_sanitize(item, path=f"{path}[]", allowlisted=False)
            for item in value
        ]
    return value


def _resolve_secret_refs(value: JsonValue | None, *, path: str) -> JsonValue | None:
    if _is_typed_secret_ref(value):
        name = str(value["name"])
        resolved = os.environ.get(name)
        if resolved is None:
            raise InvalidArtifactRequest(f"secret ref at {path} is not available in the environment")
        return resolved
    if _is_redacted_ref(value):
        raise InvalidArtifactRequest(f"redacted executable request value at {path} cannot be resolved")
    if isinstance(value, Mapping):
        return {
            str(key): _resolve_secret_refs(item, path=f"{path}.{key}")
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _resolve_secret_refs(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    return value


def _contains_redacted_literal(value: JsonValue | None) -> bool:
    if value == REDACTED_VALUE:
        return True
    if isinstance(value, Mapping):
        return any(_contains_redacted_literal(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_redacted_literal(item) for item in value)
    return False


def _find_redacted_ref(value: JsonValue | None, *, path: str = "$") -> str | None:
    if _is_redacted_ref(value):
        return path
    if isinstance(value, Mapping):
        for key, item in value.items():
            found = _find_redacted_ref(item, path=f"{path}.{key}")
            if found is not None:
                return found
    if isinstance(value, list):
        for index, item in enumerate(value):
            found = _find_redacted_ref(item, path=f"{path}[{index}]")
            if found is not None:
                return found
    return None


def _is_typed_secret_ref(value: JsonValue | None) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("type") in SECRET_REF_TYPES
        and isinstance(value.get("name"), str)
        and bool(str(value.get("name")).strip())
    )


def _is_redacted_ref(value: JsonValue | None) -> bool:
    return isinstance(value, Mapping) and value.get("type") == "redacted"


def _dict_or_empty(value: JsonValue | None) -> dict[str, JsonValue]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): item for key, item in value.items()}
