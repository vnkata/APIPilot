from __future__ import annotations

import json
from types import SimpleNamespace

from tests.fakes.http import FakeJsonResponse


def test_sync_requestor_unflattens_nested_request_bodies():
    from api_testing.generators.requestor import unflatten_dict

    assert unflatten_dict({"user.name": "Ada", "user.age": 36}) == {
        "user": {"name": "Ada", "age": 36}
    }


def test_sync_requestor_records_har_entries_and_reports(tmp_path, monkeypatch):
    import api_testing.generators.requestor as requestor_module
    from api_testing.generators.requestor import Requestor
    from api_testing.generators.status_code_peport import StatusCodeReport
    from api_testing.models.http_data import RequestData

    captured = {}

    def fake_request(method, url, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeJsonResponse({"id": 1}, status_code=201)

    StatusCodeReport.reset_shared()
    monkeypatch.setattr(requestor_module.requests, "request", fake_request)

    requestor = Requestor("http://example.test", cache_dir=str(tmp_path))
    response = requestor.exec(
        RequestData(
            uuid="post-/items",
            endpoint_path="/items",
            http_method="POST",
            mime_type="application/json",
            body={"name": "Ada"},
            expected_code="2xx",
        )
    )
    requestor.flush()

    har_files = list((tmp_path / "history").glob("*.har"))
    report = json.loads((tmp_path / "reports.json").read_text(encoding="utf-8"))
    har = json.loads(har_files[0].read_text(encoding="utf-8"))

    assert response.status_code == 201
    assert captured["method"] == "POST"
    assert captured["url"] == "http://example.test/items"
    assert captured["kwargs"]["json"] == {"name": "Ada"}
    assert report == {"post-/items": {"201": 1}}
    assert len(har_files) == 1
    assert har["log"]["entries"][0]["response"]["status"] == 201


def test_status_code_report_shared_instances_are_isolated_by_report_file(tmp_path):
    from api_testing.generators.status_code_peport import StatusCodeReport

    first_path = tmp_path / "first" / "reports.json"
    second_path = tmp_path / "second" / "reports.json"
    StatusCodeReport.reset_shared()

    first = StatusCodeReport.make_shared(str(first_path))
    second = StatusCodeReport.make_shared(str(second_path))
    first.add("get-/items", 200)
    second.add("post-/items", 201)
    first.save()
    second.save()

    assert first is not second
    assert first_path.read_text(encoding="utf-8") != second_path.read_text(
        encoding="utf-8"
    )


def test_dynamic_constraint_miner_samples_available_test_cases_when_fewer_than_50(
    tmp_path,
    monkeypatch,
):
    import api_testing.constraint.dynamic_constraint_miner as module
    from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner

    class FakeTestCaseFileManager:
        def __init__(self, cache_dir):
            self.cache_dir = cache_dir

        def parse_test_cases_from_history(self):
            return [SimpleNamespace(test_case_id=str(index)) for index in range(2)]

        def save_test_cases(self):
            return None

    captured = {}

    def fake_generate(self, test_cases, output_path):
        captured["count"] = len(test_cases)
        captured["output_path"] = output_path

    monkeypatch.setattr(module, "TestCaseFileManager", FakeTestCaseFileManager)
    monkeypatch.setattr(DynamicConstraintMiner, "generate_dtrace_file", fake_generate)

    miner = object.__new__(DynamicConstraintMiner)
    miner.cache_dir = tmp_path
    miner.DTRACE_FILENAME = "test_cases.dtrace"
    miner._cache_path = lambda filename: tmp_path / filename

    miner.extract_dtraces()

    assert captured == {
        "count": 2,
        "output_path": tmp_path / "test_cases.dtrace",
    }
