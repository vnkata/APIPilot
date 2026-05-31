"""OpenAPI parsing helpers for backend write-flow previews."""

from __future__ import annotations

import json
from typing import Any

from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.write_models import OpenAPIOperation, OpenAPIPreview


SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}


def preview_openapi_operations(content: str) -> OpenAPIPreview:
    document = load_openapi_document(content)
    info = _mapping(document.get("info"), "info")
    paths = _mapping(document.get("paths"), "paths")
    title = str(info.get("title") or "Untitled API")
    version = _optional_str(info.get("version"))

    operations: list[OpenAPIOperation] = []
    normalized_operations: dict[str, dict[str, Any]] = {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = path_item.get("parameters", [])
        for method, operation in path_item.items():
            method_lower = str(method).lower()
            if method_lower not in SUPPORTED_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            operation_id = f"{method_lower}-{path}"
            response_statuses = sorted(
                str(status)
                for status in (operation.get("responses") or {}).keys()
            )
            preview = OpenAPIOperation(
                operation_id=operation_id,
                display_operation_id=_optional_str(operation.get("operationId")),
                method=method_lower,
                path=str(path),
                summary=_optional_str(operation.get("summary")),
                has_request_body=isinstance(operation.get("requestBody"), dict),
                response_statuses=response_statuses,
            )
            operations.append(preview)
            normalized_operations[operation_id] = _normalized_operation(
                operation_id,
                method_lower,
                str(path),
                path_parameters,
                operation,
            )

    if not operations:
        raise InvalidArtifactRequest("OpenAPI document does not define operations")

    return OpenAPIPreview(
        title=title,
        version=version,
        operations=sorted(operations, key=lambda item: item.operation_id),
        normalized_specification={"operations": normalized_operations},
    )


def load_openapi_document(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        try:
            from ruamel.yaml import YAML

            payload = YAML(typ="safe").load(content)
        except Exception as exc:  # pragma: no cover - depends on optional parser details
            raise InvalidArtifactRequest("Spec content must be valid JSON or YAML") from exc

    if not isinstance(payload, dict):
        raise InvalidArtifactRequest("Spec content must be a JSON object")
    if not payload.get("openapi") and not payload.get("swagger"):
        raise InvalidArtifactRequest("Spec content must include openapi or swagger")
    _mapping(payload.get("info"), "info")
    _mapping(payload.get("paths"), "paths")
    return payload


def _normalized_operation(
    operation_id: str,
    method: str,
    path: str,
    path_parameters: Any,
    operation: dict[str, Any],
) -> dict[str, Any]:
    parameters = {}
    for parameter in _iter_parameters(path_parameters, operation.get("parameters", [])):
        name = parameter.get("name")
        if name is None:
            continue
        parameters[str(name)] = {
            "name": str(name),
            "in_value": parameter.get("in"),
            "description": parameter.get("description"),
            "required": parameter.get("required"),
            "schema": parameter.get("schema") or {},
        }

    responses = {}
    for status, response in (operation.get("responses") or {}).items():
        response_map = response if isinstance(response, dict) else {}
        responses[str(status)] = {
            "status_code": str(status),
            "description": response_map.get("description"),
            "content": response_map.get("content") or {},
        }

    return {
        "uuid": operation_id,
        "operation_id": operation.get("operationId"),
        "endpoint_path": path,
        "http_method": method,
        "summary": operation.get("summary"),
        "description": operation.get("description"),
        "tags": operation.get("tags"),
        "parameters": parameters,
        "request_body": operation.get("requestBody") or {},
        "responses": responses,
    }


def _iter_parameters(*parameter_lists):
    for parameter_list in parameter_lists:
        if isinstance(parameter_list, list):
            for parameter in parameter_list:
                if isinstance(parameter, dict):
                    yield parameter


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidArtifactRequest(f"OpenAPI document must include {field_name}")
    return value


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)

