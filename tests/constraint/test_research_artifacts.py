from __future__ import annotations

import json

import pytest

from api_testing.constraint.research_artifacts import (
    LABEL_VALUES,
    ResearchCaseEvidence,
    ResearchPairLabel,
    research_pair_id,
    load_case_evidence,
    load_pair_labels,
    summarize_research_artifacts,
    write_case_evidence,
    write_pair_labels_atomic,
)


def test_pair_label_csv_round_trips_and_creates_backup_on_update(tmp_path):
    csv_path = tmp_path / "constraint_pair_labels.csv"
    labels = [
        ResearchPairLabel(
            run_name="Run A",
            combination_id="combo-1",
            operation_id="get-/items",
            property_path="return.id",
            relation="STATIC_STRONGER",
            status="UNRESOLVED",
            static_constraint="return.id in [1,2]",
            dynamic_constraint="return.id >= 1",
            final_constraint="",
            runtime_recommendation="SUPPORT_STATIC",
            suggested_static_label="TP",
            suggested_dynamic_label="FP",
            suggested_combined_label="",
            static_label="TP",
            dynamic_label="FP",
            combined_label="",
            notes="reviewed",
            updated_at="2026-06-04T00:00:00Z",
        )
    ]

    write_pair_labels_atomic(csv_path, labels)
    first = load_pair_labels(csv_path)
    labels[0].notes = "updated"
    write_pair_labels_atomic(csv_path, labels)

    assert {label.value for label in LABEL_VALUES} == {"TP", "FP", "UNSURE"}
    assert first[0].static_label == "TP"
    assert load_pair_labels(csv_path)[0].notes == "updated"
    assert list(tmp_path.glob("constraint_pair_labels.csv.*.bak"))
    assert load_pair_labels(csv_path)[0].research_pair_id == research_pair_id(
        run_name="Run A",
        operation_id="get-/items",
        property_path="return.id",
        static_constraint="return.id in [1,2]",
        dynamic_constraint="return.id >= 1",
    )


def test_pair_label_csv_loads_legacy_rows_without_research_pair_id(tmp_path):
    csv_path = tmp_path / "constraint_pair_labels.csv"
    legacy_fields = [
        field
        for field in ResearchPairLabel.fieldnames()
        if field not in {"research_pair_id", "orphaned"}
    ]
    csv_path.write_text(
        ",".join(legacy_fields) + "\n"
        "Run A,combo-1,get-/items,return.id,STATIC_STRONGER,UNRESOLVED,"
        "static,dynamic,,SUPPORT_STATIC,TP,FP,,UNSURE,UNSURE,,notes,2026-06-04T00:00:00Z\n",
        encoding="utf-8",
    )

    labels = load_pair_labels(csv_path)

    assert labels[0].research_pair_id == research_pair_id(
        run_name="Run A",
        operation_id="get-/items",
        property_path="return.id",
        static_constraint="static",
        dynamic_constraint="dynamic",
    )
    assert labels[0].orphaned is False


def test_pair_label_csv_rejects_unknown_label(tmp_path):
    csv_path = tmp_path / "constraint_pair_labels.csv"
    csv_path.write_text(
        ",".join(ResearchPairLabel.fieldnames()) + "\n"
        "rp_invalid,Run A,combo-1,get-/items,return.id,STATIC_STRONGER,UNRESOLVED,"
        "static,dynamic,,SUPPORT_STATIC,TP,FP,,MAYBE,FP,,notes,2026-06-04T00:00:00Z,false\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid static_label"):
        load_pair_labels(csv_path)


def test_case_evidence_jsonl_round_trips_and_stays_sanitized(tmp_path):
    evidence_path = tmp_path / "counter_example_case_results.jsonl"
    evidence = [
        ResearchCaseEvidence(
            pair_id="combo-1",
            combination_id="combo-legacy",
            case_id="case-1",
            request_summary={"method": "GET", "path": "/items", "headers": "<REDACTED>"},
            response_summary={"status_code": 200, "body": {"token": "<REDACTED>"}},
            runtime_verdict="STATIC_WIN",
            runtime_recommendation="SUPPORT_STATIC",
            invalid_reason="",
            invalid_detail="",
            planner_status="generated",
            planner_error_kind="",
            weak_evidence=False,
            execution_metadata={"duration_ms": 5},
        )
    ]

    write_case_evidence(evidence_path, evidence)

    loaded = load_case_evidence(evidence_path)
    rendered = evidence_path.read_text(encoding="utf-8")
    assert loaded[0].runtime_verdict == "STATIC_WIN"
    assert loaded[0].combination_id == "combo-legacy"
    assert loaded[0].weak_evidence is False
    assert "secret" not in rendered.lower()
    assert json.loads(rendered.splitlines()[0])["response_summary"]["body"]["token"] == (
        "<REDACTED>"
    )


def test_research_summary_counts_labels_relations_and_invalid_reasons():
    labels = [
        ResearchPairLabel(
            run_name="Run A",
            combination_id="combo-1",
            operation_id="get-/items",
            property_path="return.id",
            relation="STATIC_STRONGER",
            status="UNRESOLVED",
            static_constraint="static",
            dynamic_constraint="dynamic",
            final_constraint="",
            runtime_recommendation="SUPPORT_STATIC",
            suggested_static_label="TP",
            suggested_dynamic_label="FP",
            suggested_combined_label="",
            static_label="TP",
            dynamic_label="FP",
            combined_label="",
            notes="",
            updated_at="2026-06-04T00:00:00Z",
        ),
        ResearchPairLabel(
            run_name="Run A",
            combination_id="combo-2",
            operation_id="get-/items",
            property_path="return.name",
            relation="UNKNOWN",
            status="UNRESOLVED",
            static_constraint="static",
            dynamic_constraint="dynamic",
            final_constraint="",
            runtime_recommendation="INCONCLUSIVE",
            suggested_static_label="UNSURE",
            suggested_dynamic_label="UNSURE",
            suggested_combined_label="",
            static_label="UNSURE",
            dynamic_label="UNSURE",
            combined_label="",
            notes="",
            updated_at="2026-06-04T00:00:00Z",
        ),
        ResearchPairLabel(
            run_name="Run A",
            combination_id="combo-3",
            operation_id="get-/items",
            property_path="return.status",
            relation="DYNAMIC_STRONGER",
            status="UNRESOLVED",
            static_constraint="static",
            dynamic_constraint="dynamic",
            final_constraint="",
            runtime_recommendation="SUPPORT_DYNAMIC",
            suggested_static_label="FP",
            suggested_dynamic_label="TP",
            suggested_combined_label="",
            static_label="TP",
            dynamic_label="TP",
            combined_label="",
            notes="",
            updated_at="2026-06-04T00:00:00Z",
            orphaned=True,
        ),
    ]
    evidence = [
        ResearchCaseEvidence(
            pair_id="combo-1",
            combination_id="combo-1",
            case_id="case-1",
            request_summary={"method": "GET", "path": "/items"},
            response_summary={"status_code": 200},
            runtime_verdict="STATIC_WIN",
            runtime_recommendation="SUPPORT_STATIC",
            invalid_reason="",
            invalid_detail="",
            planner_status="generated",
            planner_error_kind="",
            weak_evidence=False,
            execution_metadata={},
        ),
        ResearchCaseEvidence(
            pair_id="combo-2",
            combination_id="combo-2",
            case_id="case-2",
            request_summary={"method": "GET", "path": "/items/{id}"},
            response_summary={},
            runtime_verdict="",
            runtime_recommendation="INCONCLUSIVE",
            invalid_reason="path_param_unresolved",
            invalid_detail="missing id",
            planner_status="fallback",
            planner_error_kind="planner_parse_error",
            weak_evidence=True,
            execution_metadata={},
        ),
    ]

    summary = summarize_research_artifacts(labels, evidence)

    assert summary["relation_counts"] == {
        "DYNAMIC_STRONGER": 1,
        "STATIC_STRONGER": 1,
        "UNKNOWN": 1,
    }
    assert summary["label_counts"]["static_label"] == {"TP": 2, "UNSURE": 1}
    assert summary["invalid_runtime_counts"] == {"path_param_unresolved": 1}
    assert summary["source_metrics"]["static_label"]["tp"] == 1
    assert summary["source_metrics"]["static_label"]["precision"] == 1.0
    assert summary["source_metrics"]["static_label"]["recall"] is None
    assert summary["metric_excluded_counts"] == {"UNKNOWN": 1, "orphaned": 1}
    assert summary["source_metrics"]["dynamic_label"]["fp"] == 1
