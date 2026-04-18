from types import SimpleNamespace

from api_testing.generators.executor import Executor, Strategy
from api_testing.models.http_data import RequestData


class DummyConfiguration:
    def __init__(self):
        self.params = {}
        self.request_body = {}


def _build_executor(mutation_ratio: float = 1.0, header_mutation_ratio: float = 1.0) -> Executor:
    operation = SimpleNamespace(
        minetypes=["application/json"],
        request_body={"application/json": {}},
        uuid="op-1",
        endpoint_path="/issues",
        http_method="POST",
        parameters={},
    )
    return Executor(
        api_url="http://localhost:30000",
        strategy=Strategy.NAIVE_VALUE,
        operation=operation,
        configuration=DummyConfiguration(),
        num_test_cases=1,
        mutation_ratio=mutation_ratio,
        header_mutation_ratio=header_mutation_ratio,
    )


def _mock_user_agent(monkeypatch):
    monkeypatch.setattr(
        "api_testing.generators.executor.UserAgent",
        lambda: SimpleNamespace(random="MockedUserAgent/1.0"),
    )


def test_mutator_does_not_apply_header_mutation_for_non_4xx(monkeypatch):
    executor = _build_executor(mutation_ratio=1.0)
    _mock_user_agent(monkeypatch)

    monkeypatch.setattr(
        Executor,
        "_mutate_headers_with_generator",
        lambda self, headers: {**headers, "X-Fuzzed": "1"},
    )

    request = RequestData(
        uuid="r-1",
        endpoint_path="/issues",
        http_method="POST",
        mime_type="application/json",
        headers={"User-Agent": "base", "Accept": "*/*"},
        expected_code="2xx",
    )

    result = executor.mutator([request], body_schema={})
    assert len(result) == 1
    assert result[0].headers.get("X-Fuzzed") is None
    assert result[0].http_method == "POST"
    assert result[0].mime_type == "application/json"


def test_mutator_applies_header_and_transport_mutation_for_4xx(monkeypatch):
    executor = _build_executor(mutation_ratio=1.0)
    _mock_user_agent(monkeypatch)

    monkeypatch.setattr(
        Executor,
        "_mutate_headers_with_generator",
        lambda self, headers: {**headers, "X-Corrupt": "true"},
    )

    request = RequestData(
        uuid="r-2",
        endpoint_path="/issues",
        http_method="POST",
        mime_type="application/json",
        headers={"User-Agent": "base", "Accept": "*/*"},
        expected_code="4xx",
    )

    result = executor.mutator([request], body_schema={})
    assert len(result) == 1

    mutated = result[0]
    assert mutated.headers.get("X-Corrupt") == "true"
    assert mutated.http_method != "POST"
    assert mutated.mime_type != "application/json"
    assert mutated.headers.get("Content-Type") == mutated.mime_type


def test_mutator_skips_header_generator_when_header_ratio_zero(monkeypatch):
    executor = _build_executor(mutation_ratio=1.0, header_mutation_ratio=0.0)
    _mock_user_agent(monkeypatch)

    called = {"value": False}

    def _fuzz(self, headers):
        called["value"] = True
        return {**headers, "X-Fuzzed": "1"}

    monkeypatch.setattr(Executor, "_mutate_headers_with_generator", _fuzz)

    request = RequestData(
        uuid="r-3",
        endpoint_path="/issues",
        http_method="POST",
        mime_type="application/json",
        headers={"User-Agent": "base", "Accept": "*/*"},
        expected_code="4xx",
    )

    result = executor.mutator([request], body_schema={})
    assert len(result) == 1
    assert called["value"] is False
    assert result[0].headers.get("X-Fuzzed") is None


def test_mutator_calls_header_generator_when_header_ratio_one(monkeypatch):
    executor = _build_executor(mutation_ratio=1.0, header_mutation_ratio=1.0)
    _mock_user_agent(monkeypatch)

    called = {"value": False}

    def _fuzz(self, headers):
        called["value"] = True
        return {**headers, "X-Fuzzed": "1"}

    monkeypatch.setattr(Executor, "_mutate_headers_with_generator", _fuzz)

    request = RequestData(
        uuid="r-4",
        endpoint_path="/issues",
        http_method="POST",
        mime_type="application/json",
        headers={"User-Agent": "base", "Accept": "*/*"},
        expected_code="4xx",
    )

    result = executor.mutator([request], body_schema={})
    assert len(result) == 1
    assert called["value"] is True
    assert result[0].headers.get("X-Fuzzed") == "1"
