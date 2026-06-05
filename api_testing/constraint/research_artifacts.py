"""Research-label artifacts for constraint-pair evaluation."""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable


class ResearchLabel(str, Enum):
    TP = "TP"
    FP = "FP"
    UNSURE = "UNSURE"


LABEL_VALUES = tuple(ResearchLabel)

LABEL_FILENAME = "constraint_pair_labels.csv"
CASE_EVIDENCE_FILENAME = "counter_example_case_results.jsonl"
SUMMARY_FILENAME = "constraint_research_summary.json"

_SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
)


def research_pair_id(
    *,
    run_name: str,
    operation_id: str,
    property_path: str,
    static_constraint: str,
    dynamic_constraint: str,
) -> str:
    raw = "\x1f".join(
        [
            run_name,
            operation_id,
            property_path,
            static_constraint,
            dynamic_constraint,
        ]
    )
    return f"rp_{sha256(raw.encode('utf-8')).hexdigest()[:20]}"


@dataclass
class ResearchPairLabel:
    run_name: str
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
    combined_label: str
    notes: str
    updated_at: str
    research_pair_id: str = ""
    orphaned: bool = False

    @classmethod
    def fieldnames(cls) -> list[str]:
        return [
            "research_pair_id",
            "run_name",
            "combination_id",
            "operation_id",
            "property_path",
            "relation",
            "status",
            "static_constraint",
            "dynamic_constraint",
            "final_constraint",
            "runtime_recommendation",
            "suggested_static_label",
            "suggested_dynamic_label",
            "suggested_combined_label",
            "static_label",
            "dynamic_label",
            "combined_label",
            "notes",
            "updated_at",
            "orphaned",
        ]

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "ResearchPairLabel":
        normalized = {field: row.get(field, "") or "" for field in cls.fieldnames()}
        normalized["orphaned"] = _parse_bool(normalized.get("orphaned"))
        item = cls(**normalized)
        if not item.research_pair_id:
            item.research_pair_id = research_pair_id(
                run_name=item.run_name,
                operation_id=item.operation_id,
                property_path=item.property_path,
                static_constraint=item.static_constraint,
                dynamic_constraint=item.dynamic_constraint,
            )
        item.validate()
        return item

    def validate(self) -> None:
        for field in (
            "suggested_static_label",
            "suggested_dynamic_label",
            "suggested_combined_label",
            "static_label",
            "dynamic_label",
            "combined_label",
        ):
            value = getattr(self, field)
            if value and value not in {label.value for label in LABEL_VALUES}:
                raise ValueError(f"invalid {field}: {value}")

    def to_row(self) -> dict[str, str]:
        self.validate()
        if not self.research_pair_id:
            self.research_pair_id = research_pair_id(
                run_name=self.run_name,
                operation_id=self.operation_id,
                property_path=self.property_path,
                static_constraint=self.static_constraint,
                dynamic_constraint=self.dynamic_constraint,
            )
        row = {field: str(getattr(self, field) or "") for field in self.fieldnames()}
        row["orphaned"] = "true" if self.orphaned else "false"
        return row


@dataclass
class ResearchCaseEvidence:
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

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ResearchCaseEvidence":
        return cls(
            pair_id=str(record.get("pair_id", "")),
            combination_id=str(record.get("combination_id") or record.get("pair_id") or ""),
            case_id=str(record.get("case_id", "")),
            request_summary=_ensure_mapping(record.get("request_summary")),
            response_summary=_ensure_mapping(record.get("response_summary")),
            runtime_verdict=str(record.get("runtime_verdict") or ""),
            runtime_recommendation=str(record.get("runtime_recommendation") or ""),
            invalid_reason=str(record.get("invalid_reason") or ""),
            invalid_detail=str(record.get("invalid_detail") or ""),
            planner_status=str(record.get("planner_status") or ""),
            planner_error_kind=str(record.get("planner_error_kind") or ""),
            weak_evidence=bool(record.get("weak_evidence", False)),
            execution_metadata=_ensure_mapping(record.get("execution_metadata")),
        )

    def to_record(self) -> dict[str, Any]:
        return _sanitize_for_artifact(asdict(self))


def load_pair_labels(path: Path) -> list[ResearchPairLabel]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [ResearchPairLabel.from_row(row) for row in csv.DictReader(handle)]


def write_pair_labels_atomic(
    path: Path,
    labels: Iterable[ResearchPairLabel],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_name(f"{path.name}.{_timestamp_compact()}.bak")
        backup.write_bytes(path.read_bytes())
    temp_path = path.with_name(f"{path.name}.tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ResearchPairLabel.fieldnames())
        writer.writeheader()
        for label in labels:
            writer.writerow(label.to_row())
    os.replace(temp_path, path)


def load_case_evidence(path: Path) -> list[ResearchCaseEvidence]:
    if not path.exists():
        return []
    evidence: list[ResearchCaseEvidence] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL evidence at line {line_number}") from exc
            if not isinstance(raw, dict):
                raise ValueError(f"invalid JSONL evidence at line {line_number}")
            evidence.append(ResearchCaseEvidence.from_record(raw))
    return evidence


def write_case_evidence(
    path: Path,
    evidence: Iterable[ResearchCaseEvidence],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for item in evidence:
            handle.write(
                json.dumps(item.to_record(), ensure_ascii=False, sort_keys=True) + "\n"
            )


def summarize_research_artifacts(
    labels: Iterable[ResearchPairLabel],
    evidence: Iterable[ResearchCaseEvidence],
) -> dict[str, Any]:
    label_items = list(labels)
    evidence_items = list(evidence)
    relation_counts = Counter(item.relation for item in label_items if item.relation)
    status_counts = Counter(item.status for item in label_items if item.status)
    invalid_counts = Counter(
        item.invalid_reason for item in evidence_items if item.invalid_reason
    )
    runtime_counts = Counter(
        item.runtime_recommendation
        for item in evidence_items
        if item.runtime_recommendation
    )
    planner_status_counts = Counter(
        item.planner_status for item in evidence_items if item.planner_status
    )
    metric_labels = [
        item
        for item in label_items
        if _metric_included(item)
    ]
    metric_excluded_counts = Counter()
    for item in label_items:
        if item.orphaned:
            metric_excluded_counts["orphaned"] += 1
        elif item.relation == "UNKNOWN":
            metric_excluded_counts["UNKNOWN"] += 1
    label_counts = {
        field: dict(Counter(getattr(item, field) for item in label_items if getattr(item, field)))
        for field in ("static_label", "dynamic_label", "combined_label")
    }
    return {
        "pair_count": len(label_items),
        "evidence_case_count": len(evidence_items),
        "relation_counts": dict(sorted(relation_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "label_counts": label_counts,
        "runtime_recommendation_counts": dict(sorted(runtime_counts.items())),
        "invalid_runtime_counts": dict(sorted(invalid_counts.items())),
        "planner_status_counts": dict(sorted(planner_status_counts.items())),
        "metric_excluded_counts": dict(sorted(metric_excluded_counts.items())),
        "source_metrics": {
            field: _label_metrics(metric_labels, field)
            for field in ("static_label", "dynamic_label", "combined_label")
        },
    }


def suggested_labels_for_runtime(runtime_recommendation: str | None) -> tuple[str, str, str]:
    recommendation = (runtime_recommendation or "").upper()
    if recommendation == "SUPPORT_STATIC":
        return "TP", "FP", ""
    if recommendation == "SUPPORT_DYNAMIC":
        return "FP", "TP", ""
    return "UNSURE", "UNSURE", ""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _label_metrics(labels: list[ResearchPairLabel], field: str) -> dict[str, Any]:
    values = [getattr(item, field) for item in labels if getattr(item, field)]
    tp = sum(1 for value in values if value == "TP")
    fp = sum(1 for value in values if value == "FP")
    unsure = sum(1 for value in values if value == "UNSURE")
    denominator = tp + fp
    precision = round(tp / denominator, 4) if denominator else None
    recall = None
    f1 = None
    return {
        "tp": tp,
        "fp": fp,
        "unsure": unsure,
        "evaluated": denominator,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _sanitize_for_artifact(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if any(part in str(key).lower() for part in _SENSITIVE_KEY_PARTS):
                sanitized[str(key)] = "<REDACTED>"
            else:
                sanitized[str(key)] = _sanitize_for_artifact(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_artifact(item) for item in value]
    if isinstance(value, str) and _looks_sensitive(value):
        return "<REDACTED>"
    return value


def _looks_sensitive(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("bearer ") or any(
        marker in lowered for marker in ("api_key=", "token=", "password=", "secret=")
    )


def _ensure_mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _metric_included(label: ResearchPairLabel) -> bool:
    return not label.orphaned and label.relation != "UNKNOWN"


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
