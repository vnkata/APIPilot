import csv
import json
from pathlib import Path

from endpoint_500_report import generate_endpoint_500_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_generate_report_counts_each_endpoint_once_for_500(tmp_path: Path):
    cache_dir = tmp_path / "cache_case"
    history_dir = cache_dir / "history"

    # Minimal cached spec format with 3 endpoints.
    spec_payload = {
        "operations": {
            "get-/issues": {
                "http_method": "get",
                "endpoint_path": "/issues",
            },
            "post-/projects/{id}/issues": {
                "http_method": "post",
                "endpoint_path": "/projects/{id}/issues",
            },
            "delete-/projects/{id}/issues/{issue_iid}": {
                "http_method": "delete",
                "endpoint_path": "/projects/{id}/issues/{issue_iid}",
            },
        }
    }
    _write_json(cache_dir / "specification.json", spec_payload)

    # Two 500s for same endpoint + one non-500.
    har_payload = {
        "log": {
            "entries": [
                {
                    "_id": "e1",
                    "request": {"method": "GET", "path_template": "/issues"},
                    "response": {"status": 500},
                },
                {
                    "_id": "e2",
                    "request": {"method": "GET", "path_template": "/issues"},
                    "response": {"status": 500},
                },
                {
                    "_id": "e3",
                    "request": {"method": "POST", "path_template": "/projects/{id}/issues"},
                    "response": {"status": 400},
                },
            ]
        }
    }
    _write_json(history_dir / "session.har", har_payload)

    output_csv, output_summary, summary = generate_endpoint_500_report(cache_dir)

    assert output_csv.exists()
    assert output_summary.exists()

    with output_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    row_map = {row["endpoint"]: row for row in rows}

    assert row_map["get-/issues"]["has_500"] == "1"
    assert row_map["get-/issues"]["total_500_occurrences"] == "2"

    assert row_map["post-/projects/{id}/issues"]["has_500"] == "0"
    assert row_map["delete-/projects/{id}/issues/{issue_iid}"]["has_500"] == "0"

    # Unique endpoint count with 500 must be 1, even if endpoint has multiple 500 entries.
    assert summary["total_endpoints_with_500"] == 1
    assert summary["total_endpoints_in_spec"] == 3


def test_generate_report_accepts_history_folder_input(tmp_path: Path):
    cache_dir = tmp_path / "cache_case"
    history_dir = cache_dir / "history"

    spec_payload = {
        "operations": {
            "head-/issues": {
                "http_method": "head",
                "endpoint_path": "/issues",
            }
        }
    }
    _write_json(cache_dir / "specification.json", spec_payload)

    har_payload = {
        "log": {
            "entries": [
                {
                    "_id": "e-head",
                    "request": {"method": "HEAD", "path_template": "/issues"},
                    "response": {"status": 500},
                }
            ]
        }
    }
    _write_json(history_dir / "session.har", har_payload)

    output_csv, output_summary, summary = generate_endpoint_500_report(history_dir)

    assert output_csv.parent == history_dir
    assert output_summary.parent == history_dir
    assert summary["total_endpoints_with_500"] == 1
