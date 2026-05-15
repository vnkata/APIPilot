"""Shared in-process lookup index for explorer read services."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import hashlib

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.read_services.constraint_explorer import (
    ConstraintExplorerService,
)
from api_testing.backend.domain.errors import ArtifactNotFound
from api_testing.backend.domain.models import ConstraintExplorerEntry


_PARTICIPATING_ARTIFACTS = (
    "specification",
    "reports",
    "test_cases_json",
    "constraint_miner",
    "static_constraint_miner",
    "static_constraint_miner_request_response",
    "static_constraint_miner_response_properties",
    "dynamic_constraint_miner",
    "invariants_csv",
    "semantic_property_dependency_graph",
    "heuristic_edges",
    "gpt_edges",
    "dependency_sequences",
)
_FileSignature = tuple[int, int]
_CacheKey = tuple[str, tuple[tuple[str, _FileSignature | None], ...]]


@dataclass(frozen=True, slots=True)
class RunExplorerIndex:
    operations: dict[str, JsonValue]
    operation_keys: dict[str, str]
    operation_ids_by_key: dict[str, str]
    constraints_by_operation: dict[str, list[ConstraintExplorerEntry]] = field(
        default_factory=dict
    )
    constraints_by_operation_property: dict[
        tuple[str, str], list[ConstraintExplorerEntry]
    ] = field(default_factory=dict)
    report_status_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    test_case_status_counts: dict[str, dict[str, int]] = field(default_factory=dict)

    def operation_key(self, operation_id: str) -> str:
        return self.operation_keys.get(operation_id, operation_key(operation_id))

    def operation_id_for_key(self, operation_key_value: str) -> str | None:
        return self.operation_ids_by_key.get(operation_key_value)


class RunExplorerIndexService:
    """Builds small cross-artifact lookup maps used by explorer services."""

    def __init__(
        self,
        repository: ArtifactRepositoryProtocol,
        constraint_explorer: ConstraintExplorerService,
    ) -> None:
        self.repository = repository
        self.constraint_explorer = constraint_explorer
        self._values: dict[_CacheKey, RunExplorerIndex] = {}

    def get_index(self, run_name: str) -> RunExplorerIndex:
        self.repository.get_run(run_name)
        key = self._cache_key(run_name)
        cached = self._values.get(key)
        if cached is not None:
            return cached
        index = self._build_index(run_name)
        self._values[key] = index
        return index

    def _cache_key(self, run_name: str) -> _CacheKey:
        return (
            run_name,
            tuple(
                (artifact_id, self.repository.artifact_signature(run_name, artifact_id))
                for artifact_id in _PARTICIPATING_ARTIFACTS
            ),
        )

    def _build_index(self, run_name: str) -> RunExplorerIndex:
        operations = _operations(self.repository, run_name)
        operation_keys = {
            operation_id: operation_key(operation_id) for operation_id in operations
        }
        operation_ids_by_key = {value: key for key, value in operation_keys.items()}

        constraints_by_operation: dict[str, list[ConstraintExplorerEntry]] = defaultdict(list)
        constraints_by_operation_property: dict[
            tuple[str, str], list[ConstraintExplorerEntry]
        ] = defaultdict(list)
        for constraint in self.constraint_explorer.all_entries(run_name):
            constraints_by_operation[constraint.operation_id].append(constraint)
            constraints_by_operation_property[
                (constraint.operation_id, constraint.property_path)
            ].append(constraint)

        return RunExplorerIndex(
            operations=operations,
            operation_keys=operation_keys,
            operation_ids_by_key=operation_ids_by_key,
            constraints_by_operation=dict(constraints_by_operation),
            constraints_by_operation_property=dict(constraints_by_operation_property),
            report_status_counts=_report_status_counts(self.repository, run_name),
            test_case_status_counts=_test_case_status_counts(self.repository, run_name),
        )


def operation_key(operation_id: str) -> str:
    digest = hashlib.sha256(operation_id.encode("utf-8")).hexdigest()[:20]
    return f"op_{digest}"


def _operations(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
) -> dict[str, JsonValue]:
    try:
        raw = repository.read_json_artifact(run_name, "specification")
    except ArtifactNotFound:
        return {}
    spec = raw if isinstance(raw, dict) else {}
    operations = spec.get("operations", {})
    return operations if isinstance(operations, dict) else {}


def _report_status_counts(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
) -> dict[str, dict[str, int]]:
    try:
        raw = repository.read_json_artifact(run_name, "reports")
    except ArtifactNotFound:
        return {}
    payload = raw if isinstance(raw, dict) else {}
    result: dict[str, dict[str, int]] = {}
    for operation_id, statuses in payload.items():
        if not isinstance(statuses, dict):
            continue
        result[str(operation_id)] = {
            str(status): int(count)
            for status, count in statuses.items()
            if isinstance(count, int)
        }
    return result


def _test_case_status_counts(
    repository: ArtifactRepositoryProtocol,
    run_name: str,
) -> dict[str, dict[str, int]]:
    try:
        raw = repository.read_json_artifact(run_name, "test_cases_json")
    except ArtifactNotFound:
        return {}
    records = raw if isinstance(raw, list) else []
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        if not isinstance(record, dict):
            continue
        operation_id = record.get("operation_id")
        status_code = record.get("status_code")
        if operation_id is None or status_code is None:
            continue
        counts[str(operation_id)][str(status_code)] += 1
    return {operation_id: dict(statuses) for operation_id, statuses in counts.items()}
