from __future__ import annotations

import csv
import json
from pathlib import Path

from fastapi.testclient import TestClient

from tests.fixtures.backend_artifacts import (
    add_combination_artifacts,
    build_artifact_cache,
    write_json,
)


def _client(cache_root: Path) -> TestClient:
    from api_testing.backend.app import create_app
    from api_testing.backend.settings import BackendSettings

    return TestClient(create_app(BackendSettings(cache_root=cache_root)))


def _cache_with_research_artifacts(tmp_path: Path) -> Path:
    return add_combination_artifacts(build_artifact_cache(tmp_path))


def _write_evidence(cache_root: Path, combination_id: str) -> None:
    run_dir = cache_root / "Run A"
    (run_dir / "counter_example_case_results.jsonl").write_text(
        json.dumps(
            {
                "pair_id": combination_id,
                "case_id": "case-1",
                "request_summary": {"method": "GET", "path": "/items"},
                "response_summary": {"status_code": 200},
                "runtime_verdict": "",
                "runtime_recommendation": "INCONCLUSIVE",
                "invalid_reason": "path_param_unresolved",
                "execution_metadata": {},
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_research_summary_and_entries_initialize_from_non_equivalent_pairs(tmp_path):
    cache_root = _cache_with_research_artifacts(tmp_path)
    client = _client(cache_root)

    initial_entries = client.get("/api/v1/runs/Run%20A/constraints/research/entries")
    assert initial_entries.status_code == 200
    _write_evidence(cache_root, initial_entries.json()["items"][0]["combination_id"])

    summary_response = client.get("/api/v1/runs/Run%20A/constraints/research/summary")
    entries_response = client.get("/api/v1/runs/Run%20A/constraints/research/entries")

    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["pair_count"] == 1
    assert summary["relation_counts"] == {"DISJOINT": 1}
    assert summary["invalid_runtime_counts"] == {"path_param_unresolved": 1}
    assert summary["label_counts"]["static_label"] == {"UNSURE": 1}

    assert entries_response.status_code == 200
    entries = entries_response.json()
    assert entries["pagination"]["total"] == 1
    entry = entries["items"][0]
    assert entry["relation"] == "DISJOINT"
    assert entry["research_pair_id"].startswith("rp_")
    assert entry["orphaned"] is False
    assert entry["metric_included"] is True
    assert entry["static_label"] == "UNSURE"
    assert entry["dynamic_label"] == "UNSURE"
    assert entry["suggested_static_label"] == "UNSURE"
    assert entry["evidence_case_count"] == 1


def test_research_label_save_updates_canonical_csv_atomically(tmp_path):
    cache_root = _cache_with_research_artifacts(tmp_path)
    client = _client(cache_root)
    entry = client.get("/api/v1/runs/Run%20A/constraints/research/entries").json()[
        "items"
    ][0]

    response = client.put(
        f"/api/v1/runs/Run%20A/constraints/research/entries/{entry['research_pair_id']}/labels",
        json={
            "static_label": "TP",
            "dynamic_label": "FP",
            "combined_label": None,
            "notes": "Reviewed for paper metrics.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["static_label"] == "TP"
    assert payload["dynamic_label"] == "FP"
    assert payload["notes"] == "Reviewed for paper metrics."

    csv_path = cache_root / "Run A" / "constraint_pair_labels.csv"
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["research_pair_id"] == entry["research_pair_id"]
    assert rows[0]["static_label"] == "TP"
    assert rows[0]["dynamic_label"] == "FP"
    assert list(csv_path.parent.glob("constraint_pair_labels.csv.*.bak"))


def test_research_detail_returns_sanitized_evidence_and_csv_download(tmp_path):
    cache_root = _cache_with_research_artifacts(tmp_path)
    client = _client(cache_root)
    entry = client.get("/api/v1/runs/Run%20A/constraints/research/entries").json()[
        "items"
    ][0]
    _write_evidence(cache_root, entry["research_pair_id"])

    detail_response = client.get(
        f"/api/v1/runs/Run%20A/constraints/research/entries/{entry['research_pair_id']}"
    )
    csv_response = client.get("/api/v1/runs/Run%20A/constraints/research/labels.csv")

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["research_pair_id"] == entry["research_pair_id"]
    assert detail["operation_spec_excerpt"]["path"] == "/items"
    assert "parameters" in detail["operation_spec_excerpt"]
    assert detail["evidence_cases"][0]["invalid_reason"] == "path_param_unresolved"
    assert "secret" not in json.dumps(detail).lower()

    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "constraint_pair_labels.csv" in csv_response.headers["content-disposition"]
    assert "combination_id" in csv_response.text.splitlines()[0]


def test_research_entries_preserve_orphaned_csv_rows_and_filter_them(tmp_path):
    cache_root = _cache_with_research_artifacts(tmp_path)
    client = _client(cache_root)
    active_entry = client.get("/api/v1/runs/Run%20A/constraints/research/entries").json()[
        "items"
    ][0]
    csv_path = cache_root / "Run A" / "constraint_pair_labels.csv"
    with csv_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv.DictReader(csv_path.open("r", encoding="utf-8")).fieldnames or []))
        writer.writerow(
            {
                "research_pair_id": "rp_orphan",
                "run_name": "Run A",
                "combination_id": "cmb_orphan",
                "operation_id": "get-/old",
                "property_path": "return.old",
                "relation": "STATIC_STRONGER",
                "status": "UNRESOLVED",
                "static_constraint": "old static",
                "dynamic_constraint": "old dynamic",
                "final_constraint": "",
                "runtime_recommendation": "",
                "suggested_static_label": "UNSURE",
                "suggested_dynamic_label": "UNSURE",
                "suggested_combined_label": "",
                "static_label": "TP",
                "dynamic_label": "UNSURE",
                "combined_label": "",
                "notes": "old label",
                "updated_at": "2026-06-04T00:00:00Z",
                "orphaned": "false",
            }
        )

    default_response = client.get("/api/v1/runs/Run%20A/constraints/research/entries")
    orphan_response = client.get(
        "/api/v1/runs/Run%20A/constraints/research/entries?orphaned=true"
    )

    assert default_response.status_code == 200
    assert [item["research_pair_id"] for item in default_response.json()["items"]] == [
        active_entry["research_pair_id"]
    ]
    assert orphan_response.status_code == 200
    orphan = orphan_response.json()["items"][0]
    assert orphan["research_pair_id"] == "rp_orphan"
    assert orphan["orphaned"] is True
    assert orphan["metric_included"] is False


def test_research_api_rejects_old_combination_format(tmp_path):
    cache_root = build_artifact_cache(tmp_path)
    run_dir = cache_root / "Run A"
    write_json(
        run_dir / "combine_constraint_miners.json",
        {
            "get-/items": {
                "return.id": {
                    "endpoint": "get-/items",
                    "property": "return.id",
                    "static_constraint": "exists(return.id)",
                    "dynamic_constraint": "exists(return.id)",
                    "status": "COMBINED_EQUIVALENT",
                    "final_constraint": "exists(return.id)",
                }
            }
        },
    )
    client = _client(cache_root)

    response = client.get("/api/v1/runs/Run%20A/constraints/research/entries")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"
    assert "regenerate required" in response.json()["error"]["message"]


def test_research_api_rejects_stale_static_stronger_resolved_artifact(tmp_path):
    cache_root = build_artifact_cache(tmp_path)
    run_dir = cache_root / "Run A"
    write_json(
        run_dir / "combine_constraint_miners.json",
        {
            "get-/items": {
                "return.id": {
                    "endpoint": "get-/items",
                    "property": "return.id",
                    "static_constraint": "in(return.id, [1, 2])",
                    "dynamic_constraint": "gte(return.id, 1)",
                    "status": "RESOLVED",
                    "relation": "STATIC_STRONGER",
                    "final_constraint": "in(return.id, [1, 2])",
                    "reason": "stale artifact",
                }
            }
        },
    )
    client = _client(cache_root)

    research_response = client.get("/api/v1/runs/Run%20A/constraints/research/entries")
    raw_response = client.get(
        "/api/v1/runs/Run%20A/artifacts/combine_constraint_miners/content?raw=true"
    )

    assert research_response.status_code == 400
    assert research_response.json()["error"]["code"] == "invalid_request"
    assert "regenerate required" in research_response.json()["error"]["message"]
    assert raw_response.status_code == 200
    assert "STATIC_STRONGER" in raw_response.text
