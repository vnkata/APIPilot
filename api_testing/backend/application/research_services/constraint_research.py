"""CSV-backed research review service for Combination constraint pairs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from api_testing.backend.application.querying import (
    CombinationQuery,
    MAX_PAGE_LIMIT,
    QueryOptions,
)
from api_testing.backend.application.services import ArtifactQueryService
from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest
from api_testing.constraint.research_artifacts import (
    CASE_EVIDENCE_FILENAME,
    LABEL_FILENAME,
    ResearchCaseEvidence,
    ResearchPairLabel,
    load_case_evidence,
    load_pair_labels,
    research_pair_id,
    suggested_labels_for_runtime,
    summarize_research_artifacts,
    utc_now_iso,
    write_pair_labels_atomic,
)


@dataclass(frozen=True, slots=True)
class ResearchEvidenceCase:
    pair_id: str
    combination_id: str
    case_id: str
    request_summary: dict[str, Any]
    response_summary: dict[str, Any]
    runtime_verdict: str
    runtime_recommendation: str
    invalid_reason: str
    invalid_detail: str
    planner_status: str
    planner_error_kind: str
    weak_evidence: bool
    execution_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ResearchEntry:
    run_name: str
    research_pair_id: str
    combination_id: str
    operation_id: str
    property_path: str
    relation: str
    status: str
    static_constraint: str
    dynamic_constraint: str
    final_constraint: str
    runtime_recommendation: str
    suggested_static_label: str
    suggested_dynamic_label: str
    suggested_combined_label: str
    static_label: str
    dynamic_label: str
    combined_label: str | None
    notes: str
    updated_at: str
    evidence_case_count: int
    invalid_case_count: int
    orphaned: bool
    metric_included: bool


@dataclass(frozen=True, slots=True)
class ResearchEntryPage:
    items: list[ResearchEntry]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class ResearchDetail:
    entry: ResearchEntry
    evidence_cases: list[ResearchEvidenceCase]
    operation_spec_excerpt: dict[str, Any]


class ConstraintResearchService:
    """Maintains research labels with CSV as the canonical source of truth."""

    def __init__(self, artifact_service: ArtifactQueryService, cache_root: Path) -> None:
        self.artifact_service = artifact_service
        self.cache_root = cache_root

    def get_summary(self, run_name: str) -> dict[str, Any]:
        labels, evidence = self._load_state(run_name)
        summary = summarize_research_artifacts(labels, evidence)
        summary["run_name"] = run_name
        summary["label_artifact"] = LABEL_FILENAME
        summary["evidence_artifact"] = CASE_EVIDENCE_FILENAME
        return summary

    def list_entries(
        self,
        run_name: str,
        *,
        relation: str | None = None,
        runtime_recommendation: str | None = None,
        invalid_reason: str | None = None,
        label_state: str | None = None,
        orphaned: bool | None = False,
        limit: int = 50,
        offset: int = 0,
    ) -> ResearchEntryPage:
        labels, evidence = self._load_state(run_name)
        entries = self._entries_from_state(run_name, labels, evidence)
        if relation:
            entries = [entry for entry in entries if entry.relation == relation]
        if runtime_recommendation:
            entries = [
                entry
                for entry in entries
                if entry.runtime_recommendation == runtime_recommendation
            ]
        if invalid_reason:
            invalid_pair_ids = {
                item.pair_id for item in evidence if item.invalid_reason == invalid_reason
            }
            invalid_combination_ids = {
                item.combination_id
                for item in evidence
                if item.invalid_reason == invalid_reason and item.combination_id
            }
            entries = [
                entry
                for entry in entries
                if entry.research_pair_id in invalid_pair_ids
                or entry.combination_id in invalid_pair_ids
                or entry.combination_id in invalid_combination_ids
            ]
        if label_state == "labeled":
            entries = [
                entry
                for entry in entries
                if entry.static_label in {"TP", "FP"} or entry.dynamic_label in {"TP", "FP"}
            ]
        elif label_state == "unlabeled":
            entries = [
                entry
                for entry in entries
                if entry.static_label == "UNSURE" and entry.dynamic_label == "UNSURE"
            ]
        if orphaned is not None:
            entries = [entry for entry in entries if entry.orphaned is orphaned]
        total = len(entries)
        page_items = entries[offset : offset + limit]
        return ResearchEntryPage(
            items=page_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_detail(self, run_name: str, combination_id: str) -> ResearchDetail:
        labels, evidence = self._load_state(run_name)
        entries = self._entries_from_state(run_name, labels, evidence)
        entry = _entry_by_identifier(entries, combination_id)
        if entry is None:
            raise ArtifactNotFound(f"Research constraint pair not found: {combination_id}")
        return ResearchDetail(
            entry=entry,
            evidence_cases=_sort_evidence_cases([
                _evidence_case(item)
                for item in evidence
                if item.pair_id == entry.research_pair_id
                or item.pair_id == entry.combination_id
                or item.combination_id == entry.combination_id
            ]),
            operation_spec_excerpt=self._operation_spec_excerpt(
                run_name,
                entry.operation_id,
            ),
        )

    def update_labels(
        self,
        run_name: str,
        combination_id: str,
        *,
        static_label: str,
        dynamic_label: str,
        combined_label: str | None,
        notes: str,
    ) -> ResearchEntry:
        labels, evidence = self._load_state(run_name)
        updated: list[ResearchPairLabel] = []
        found = False
        for label in labels:
            if label.research_pair_id == combination_id or label.combination_id == combination_id:
                label = ResearchPairLabel(
                    **{
                        **label.to_row(),
                        "static_label": static_label,
                        "dynamic_label": dynamic_label,
                        "combined_label": combined_label or "",
                        "notes": notes,
                        "updated_at": utc_now_iso(),
                    }
                )
                found = True
            updated.append(label)
        if not found:
            raise ArtifactNotFound(f"Research constraint pair not found: {combination_id}")
        write_pair_labels_atomic(self._label_path(run_name), updated)
        entry = _entry_by_identifier(
            self._entries_from_state(run_name, updated, evidence),
            combination_id,
        )
        if entry is None:
            raise ArtifactNotFound(f"Research constraint pair not found: {combination_id}")
        return entry

    def export_csv(self, run_name: str) -> str:
        self._load_state(run_name)
        return self._label_path(run_name).read_text(encoding="utf-8")

    def _load_state(
        self,
        run_name: str,
    ) -> tuple[list[ResearchPairLabel], list[ResearchCaseEvidence]]:
        pairs = self._researchable_pairs(run_name)
        label_path = self._label_path(run_name)
        labels = load_pair_labels(label_path)
        labels_by_research_id = {label.research_pair_id: label for label in labels}
        labels_by_combination_id = {label.combination_id: label for label in labels}
        changed = not label_path.exists()
        active_ids: set[str] = set()
        ordered: list[ResearchPairLabel] = []
        for pair in pairs:
            pair_id = _research_pair_id_for_pair(run_name, pair)
            active_ids.add(pair_id)
            existing = labels_by_research_id.get(pair_id) or labels_by_combination_id.get(
                pair.combination_id
            )
            if existing is None:
                ordered.append(self._label_from_pair(run_name, pair))
                changed = True
                continue
            refreshed = _refresh_label_from_pair(run_name, existing, pair)
            if refreshed.to_row() != existing.to_row():
                changed = True
            ordered.append(refreshed)
        for label in labels:
            if label.research_pair_id in active_ids:
                continue
            orphan = _mark_orphaned(label)
            if orphan.to_row() != label.to_row():
                changed = True
            ordered.append(orphan)
        if changed:
            write_pair_labels_atomic(label_path, ordered)
        return ordered, load_case_evidence(self._evidence_path(run_name))

    def _researchable_pairs(self, run_name: str):
        items = []
        offset = 0
        while True:
            page = self.artifact_service.list_combination_entries(
                run_name,
                CombinationQuery(
                    options=QueryOptions(
                        limit=MAX_PAGE_LIMIT,
                        offset=offset,
                        sort_by="property_path",
                    )
                ),
            )
            items.extend(page.items)
            offset += page.pagination.limit
            if offset >= page.pagination.total:
                break
        return [
            item
            for item in items
            if item.relation
            and item.relation != "EQUIVALENT"
            and item.static_constraint is not None
            and item.dynamic_constraint is not None
        ]

    def _label_from_pair(self, run_name: str, pair) -> ResearchPairLabel:
        static_label, dynamic_label, combined_label = suggested_labels_for_runtime(
            pair.runtime_verdict
        )
        return ResearchPairLabel(
            run_name=run_name,
            research_pair_id=_research_pair_id_for_pair(run_name, pair),
            combination_id=pair.combination_id,
            operation_id=pair.operation_id,
            property_path=pair.property_path,
            relation=pair.relation or "",
            status=pair.status,
            static_constraint=pair.static_constraint or "",
            dynamic_constraint=pair.dynamic_constraint or "",
            final_constraint=pair.final_constraint or "",
            runtime_recommendation=pair.runtime_verdict or "",
            suggested_static_label=static_label,
            suggested_dynamic_label=dynamic_label,
            suggested_combined_label=combined_label,
            static_label="UNSURE",
            dynamic_label="UNSURE",
            combined_label="",
            notes="",
            updated_at=utc_now_iso(),
            orphaned=False,
        )

    def _entries_from_state(
        self,
        run_name: str,
        labels: list[ResearchPairLabel],
        evidence: list[ResearchCaseEvidence],
    ) -> list[ResearchEntry]:
        evidence_by_pair: dict[str, list[ResearchCaseEvidence]] = {}
        for item in evidence:
            evidence_by_pair.setdefault(item.pair_id, []).append(item)
            if item.combination_id:
                evidence_by_pair.setdefault(item.combination_id, []).append(item)
        entries: list[ResearchEntry] = []
        for label in labels:
            seen_case_ids: set[str] = set()
            pair_evidence = []
            for item in [
                *evidence_by_pair.get(label.research_pair_id, []),
                *evidence_by_pair.get(label.combination_id, []),
            ]:
                if item.case_id in seen_case_ids:
                    continue
                seen_case_ids.add(item.case_id)
                pair_evidence.append(item)
            runtime_recommendation = _latest_runtime_recommendation(
                label,
                pair_evidence,
            )
            entries.append(
                ResearchEntry(
                    run_name=run_name,
                    research_pair_id=label.research_pair_id,
                    combination_id=label.combination_id,
                    operation_id=label.operation_id,
                    property_path=label.property_path,
                    relation=label.relation,
                    status=label.status,
                    static_constraint=label.static_constraint,
                    dynamic_constraint=label.dynamic_constraint,
                    final_constraint=label.final_constraint,
                    runtime_recommendation=runtime_recommendation,
                    suggested_static_label=label.suggested_static_label,
                    suggested_dynamic_label=label.suggested_dynamic_label,
                    suggested_combined_label=label.suggested_combined_label,
                    static_label=label.static_label,
                    dynamic_label=label.dynamic_label,
                    combined_label=label.combined_label or None,
                    notes=label.notes,
                    updated_at=label.updated_at,
                    evidence_case_count=len(pair_evidence),
                    invalid_case_count=sum(
                        1 for item in pair_evidence if item.invalid_reason
                    ),
                    orphaned=label.orphaned,
                    metric_included=not label.orphaned and label.relation != "UNKNOWN",
                )
            )
        return entries

    def _label_path(self, run_name: str) -> Path:
        return self._run_dir(run_name) / LABEL_FILENAME

    def _evidence_path(self, run_name: str) -> Path:
        return self._run_dir(run_name) / CASE_EVIDENCE_FILENAME

    def _run_dir(self, run_name: str) -> Path:
        run_dir = self.cache_root / run_name
        if not run_dir.exists():
            raise ArtifactNotFound(f"Run not found: {run_name}")
        return run_dir

    def _operation_spec_excerpt(
        self,
        run_name: str,
        operation_id: str,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_name)
        spec = _read_json(run_dir / "specification.json") or _read_json(
            run_dir / "baseline_specification.json"
        )
        if not isinstance(spec, dict):
            return {}
        method, path = _method_path(operation_id)
        operation = _operation_from_spec(spec, operation_id, method, path)
        if not isinstance(operation, dict):
            return {
                "method": method.lower(),
                "path": path,
                "operation_id": operation_id,
                "parameters": [],
                "request_body": {},
                "responses": {},
            }
        excerpt = {
            "method": str(
                operation.get("http_method")
                or operation.get("method")
                or method
            ).lower(),
            "path": str(operation.get("endpoint_path") or path),
            "operation_id": str(
                operation.get("operation_id")
                or operation.get("operationId")
                or operation_id
            ),
            "summary": operation.get("summary") or "",
            "description": operation.get("description") or "",
            "parameters": operation.get("parameters") or [],
            "request_body": operation.get("request_body")
            or operation.get("requestBody")
            or {},
            "responses": operation.get("responses") or {},
        }
        path_item = _path_item(spec, path)
        if isinstance(path_item, dict) and isinstance(path_item.get("parameters"), list):
            current_parameters = excerpt["parameters"]
            if isinstance(current_parameters, list):
                excerpt["parameters"] = [*path_item["parameters"], *current_parameters]
        return _bounded_excerpt(excerpt)


def _latest_runtime_recommendation(
    label: ResearchPairLabel,
    evidence: list[ResearchCaseEvidence],
) -> str:
    for item in reversed(evidence):
        if item.runtime_recommendation:
            return item.runtime_recommendation
    return label.runtime_recommendation


def _evidence_case(item: ResearchCaseEvidence) -> ResearchEvidenceCase:
    return ResearchEvidenceCase(
        pair_id=item.pair_id,
        combination_id=item.combination_id,
        case_id=item.case_id,
        request_summary=item.request_summary,
        response_summary=item.response_summary,
        runtime_verdict=item.runtime_verdict,
        runtime_recommendation=item.runtime_recommendation,
        invalid_reason=item.invalid_reason,
        invalid_detail=item.invalid_detail,
        planner_status=item.planner_status,
        planner_error_kind=item.planner_error_kind,
        weak_evidence=item.weak_evidence,
        execution_metadata=item.execution_metadata,
    )


def _research_pair_id_for_pair(run_name: str, pair) -> str:
    return research_pair_id(
        run_name=run_name,
        operation_id=pair.operation_id,
        property_path=pair.property_path,
        static_constraint=pair.static_constraint or "",
        dynamic_constraint=pair.dynamic_constraint or "",
    )


def _refresh_label_from_pair(
    run_name: str,
    label: ResearchPairLabel,
    pair,
) -> ResearchPairLabel:
    return ResearchPairLabel(
        **{
            **label.to_row(),
            "research_pair_id": _research_pair_id_for_pair(run_name, pair),
            "combination_id": pair.combination_id,
            "operation_id": pair.operation_id,
            "property_path": pair.property_path,
            "relation": pair.relation or "",
            "status": pair.status,
            "static_constraint": pair.static_constraint or "",
            "dynamic_constraint": pair.dynamic_constraint or "",
            "final_constraint": pair.final_constraint or "",
            "orphaned": False,
        }
    )


def _mark_orphaned(label: ResearchPairLabel) -> ResearchPairLabel:
    return ResearchPairLabel(**{**label.to_row(), "orphaned": True})


def _entry_by_identifier(
    entries: list[ResearchEntry],
    identifier: str,
) -> ResearchEntry | None:
    for entry in entries:
        if entry.research_pair_id == identifier or entry.combination_id == identifier:
            return entry
    return None


def _sort_evidence_cases(
    evidence: list[ResearchEvidenceCase],
) -> list[ResearchEvidenceCase]:
    return sorted(
        evidence,
        key=lambda item: (
            0 if item.invalid_reason else 1,
            item.case_id,
        ),
    )


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _method_path(operation_id: str) -> tuple[str, str]:
    if "-/" in operation_id:
        method, raw_path = operation_id.split("-", 1)
        return method.upper(), raw_path
    return "GET", operation_id if operation_id.startswith("/") else f"/{operation_id}"


def _operation_from_spec(
    spec: dict[str, Any],
    operation_id: str,
    method: str,
    path: str,
) -> dict[str, Any] | None:
    operations = spec.get("operations")
    if isinstance(operations, dict):
        operation = operations.get(operation_id)
        if isinstance(operation, dict):
            return operation
        for item in operations.values():
            if not isinstance(item, dict):
                continue
            if (
                item.get("uuid") == operation_id
                or item.get("operation_id") == operation_id
                or item.get("operationId") == operation_id
            ):
                return item
    path_item = _path_item(spec, path)
    if isinstance(path_item, dict):
        operation = path_item.get(method.lower())
        if isinstance(operation, dict):
            return operation
    return None


def _path_item(spec: dict[str, Any], path: str) -> dict[str, Any] | None:
    paths = spec.get("paths")
    if isinstance(paths, dict):
        item = paths.get(path)
        if isinstance(item, dict):
            return item
    return None


def _bounded_excerpt(value: Any, *, depth: int = 0) -> Any:
    if depth > 5:
        return "<truncated>"
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 30:
                result["<truncated>"] = True
                break
            key_str = str(key)
            if _sensitive_key(key_str):
                result[key_str] = "<REDACTED>"
            else:
                result[key_str] = _bounded_excerpt(item, depth=depth + 1)
        return result
    if isinstance(value, list):
        items = [_bounded_excerpt(item, depth=depth + 1) for item in value[:30]]
        if len(value) > 30:
            items.append({"<truncated>": True})
        return items
    if isinstance(value, str):
        return value if len(value) <= 1000 else f"{value[:1000]}..."
    return value


def _sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(
        part in lowered
        for part in (
            "authorization",
            "cookie",
            "token",
            "password",
            "secret",
            "api_key",
        )
    )
