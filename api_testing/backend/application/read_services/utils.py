"""Shared artifact read-model parsing helpers."""

from __future__ import annotations

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.domain.errors import ArtifactNotFound
from api_testing.backend.domain.models import (
    ConstraintEntry,
    GraphSimilarity,
    HttpMethod,
    InvariantGroup,
    InvariantRecord,
    SanitizedBody,
)


def read_json_list(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
    artifact_id: str,
) -> list[JsonValue]:
    try:
        raw = repository.read_json_artifact(run_name, artifact_id)
    except ArtifactNotFound:
        return []
    return raw if isinstance(raw, list) else []


def constraint_entries(value: JsonValue) -> list[ConstraintEntry]:
    if not isinstance(value, dict):
        return []
    entries: list[ConstraintEntry] = []
    for operation_id, constraints in value.items():
        if not isinstance(constraints, dict):
            continue
        for property_path, expression in constraints.items():
            entries.append(
                ConstraintEntry(
                    operation_id=str(operation_id),
                    property_path=str(property_path),
                    expression=str(expression),
                )
            )
    return sorted(
        entries,
        key=lambda item: (item.operation_id, item.property_path, item.expression),
    )


def invariant_groups(value: JsonValue) -> list[InvariantGroup]:
    if not isinstance(value, dict):
        return []
    groups: list[InvariantGroup] = []
    for operation_id, invariants in value.items():
        groups.append(
            InvariantGroup(
                operation_id=str(operation_id),
                invariants=invariants if isinstance(invariants, list) else [invariants],
            )
        )
    return sorted(groups, key=lambda item: item.operation_id)


def invariant_record(row: dict[str, str]) -> InvariantRecord:
    return InvariantRecord(
        pptname=row.get("pptname"),
        invariant=row.get("invariant"),
        invariant_type=row.get("invariantType"),
        variables=row.get("variables"),
        postman_assertion=row.get("postmanAssertion"),
    )


def operation_id_from_pptname(pptname: str | None) -> str | None:
    if not pptname:
        return None
    return pptname.split(":::", maxsplit=1)[0] or None


def graph_similarities(value: JsonValue) -> list[GraphSimilarity]:
    if not isinstance(value, list):
        return []
    similarities: list[GraphSimilarity] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        similarities.append(
            GraphSimilarity(
                value1=optional_str(item.get("value1")),
                value2=optional_str(item.get("value2")),
                in_value=optional_str(item.get("in_value")),
            )
        )
    return similarities


def body_for_response(body: SanitizedBody) -> JsonValue | None:
    if body.included:
        return body.content
    if body.preview is not None:
        return {
            "included": False,
            "truncated": body.truncated,
            "preview": body.preview,
            "size_bytes": body.size_bytes,
            "redaction_count": body.redaction_count,
        }
    return None


def http_method(value: JsonValue) -> HttpMethod | None:
    if value is None:
        return None
    try:
        return HttpMethod(str(value).lower())
    except ValueError:
        return None


def optional_str(value: JsonValue) -> str | None:
    return None if value is None else str(value)


def to_int(value: JsonValue) -> int:
    if not isinstance(value, bool | int | float | str):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def to_int_or_none(value: JsonValue) -> int | None:
    if not isinstance(value, bool | int | float | str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
