import copy
import json

import pytest
import requests

from api_testing.constraint.combine import (
    load_constraints,
    resolve_base_url,
    resolve_cache_dir,
)
from api_testing.constraint.conflict_resolver import (
    ConstraintConflictResolver,
    ConstraintRuleEvaluator,
)
from api_testing.memory.contextual_memory import ContextualMemory
from api_testing.models.http_data import ResponseData
from tests.fakes.http import FakeJsonResponse


def conflict_record():
    return {
        "get-/things": {
            "return.count": {
                "endpoint": "get-/things",
                "property": "return.count",
                "static_constraint": "gte(return.count, 0)",
                "dynamic_constraint": "return.count == 5",
                "status": "UNRESOLVED",
                "relation": "DYNAMIC_STRONGER",
                "final_constraint": None,
                "reason": "CONFLICT: Needs runtime verification.",
                "runtime_verdict": None,
                "counter_example": {
                    "target_side": "STATIC_TRUE_DYNAMIC_FALSE",
                    "concrete_property_value": 3,
                    "staged_payload": {"parameters": {"limit": 3}},
                    "server_actual_response": None,
                },
            }
        }
    }


class FakeRequestor:
    def __init__(self, status_code=200, parsed=None):
        self.status_code = status_code
        self.parsed = parsed
        self.requests = []

    def exec(self, request):
        self.requests.append(request)
        return ResponseData(
            status_code=self.status_code,
            headers={},
            cookies={},
            mime_type="application/json",
            body="",
            parsed=self.parsed,
        )


def test_resolver_keeps_dynamic_stronger_pending_from_static_only_response(tmp_path):
    resolver = ConstraintConflictResolver(
        cache_dir=tmp_path, requestor=FakeRequestor(parsed={"count": 3})
    )
    record = resolver.resolve(conflict_record())["get-/things"]["return.count"]

    assert record["runtime_verdict"] == "STATIC_WIN"
    assert record["status"] == "UNRESOLVED"
    assert record["final_constraint"] is None


def test_resolver_keeps_dynamic_stronger_unresolved_when_runtime_supports_both(tmp_path):
    resolver = ConstraintConflictResolver(
        cache_dir=tmp_path, requestor=FakeRequestor(parsed={"count": 5})
    )
    record = resolver.resolve(conflict_record())["get-/things"]["return.count"]

    assert record["runtime_verdict"] == "BOTH_TRUE"
    assert record["runtime_recommendation"] == "INCONCLUSIVE"
    assert record["status"] == "UNRESOLVED"
    assert record["final_constraint"] is None


def test_resolver_treats_dynamic_win_for_dynamic_stronger_as_contradiction(tmp_path):
    data = conflict_record()
    data["get-/things"]["return.count"]["static_constraint"] = "gte(return.count, 10)"
    resolver = ConstraintConflictResolver(
        cache_dir=tmp_path, requestor=FakeRequestor(parsed={"count": 5})
    )
    record = resolver.resolve(data)["get-/things"]["return.count"]

    assert record["runtime_verdict"] == "DYNAMIC_WIN"
    assert record["runtime_recommendation"] == "RELATION_CONTRADICTION"
    assert record["status"] == "UNRESOLVED"
    assert record["final_constraint"] is None


def test_resolver_reports_server_failure_without_combining(tmp_path):
    resolver = ConstraintConflictResolver(
        cache_dir=tmp_path, requestor=FakeRequestor(status_code=500, parsed={})
    )
    record = resolver.resolve(conflict_record())["get-/things"]["return.count"]

    assert record["runtime_verdict"] == "CONFLICT_BOTH_FALSE"
    assert record["status"] == "UNRESOLVED"
    assert record["final_constraint"] is None


def test_verify_base_url_comes_from_cached_spec_not_unrelated_config(tmp_path):
    (tmp_path / "baseline_specification.json").write_text(
        json.dumps({"servers": [{"url": "https://bills.example/"}]}),
        encoding="utf-8",
    )

    assert resolve_base_url(tmp_path, None) == "https://bills.example/"
    assert resolve_base_url(tmp_path, "https://override.example/") == "https://override.example/"


def test_resolve_cache_dir_recovers_quoted_shell_escaped_space(tmp_path):
    cache_dir = tmp_path / "Canada Holidays"
    cache_dir.mkdir()

    resolved = resolve_cache_dir(str(tmp_path / "Canada\\ Holidays"))

    assert resolved == cache_dir


def test_load_constraints_reports_required_missing_artifact(tmp_path):
    with pytest.raises(FileNotFoundError, match="static_constraint_miner.json"):
        load_constraints(tmp_path)


def test_resolver_default_http_path_does_not_depend_on_requestor_har(monkeypatch, tmp_path):
    calls = {}

    def fake_request(method, url, **kwargs):
        calls.update({"method": method, "url": url, "kwargs": kwargs})
        return FakeJsonResponse({"count": 3})

    monkeypatch.setattr(requests, "request", fake_request)
    resolver = ConstraintConflictResolver(
        cache_dir=tmp_path,
        base_url="https://example.test/",
    )
    record = resolver.resolve(conflict_record())["get-/things"]["return.count"]

    assert calls["method"] == "GET"
    assert calls["url"] == "https://example.test/things"
    assert record["runtime_verdict"] == "STATIC_WIN"


def test_resolver_uses_contextual_memory_for_unstaged_path_request(tmp_path):
    endpoint = "get-/bills/{billId}"
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.set_current(endpoint)
    memory.add({"billId": 1000})
    memory.close()

    staged = conflict_record()
    record = staged.pop("get-/things")
    record["return.count"]["endpoint"] = endpoint
    record["return.count"]["counter_example"] = None
    staged[endpoint] = record
    requestor = FakeRequestor(parsed={"count": 3})

    result = ConstraintConflictResolver(cache_dir=tmp_path, requestor=requestor).resolve(staged)
    verified = result[endpoint]["return.count"]

    assert requestor.requests[0].endpoint_path == "/bills/{billId}"
    assert requestor.requests[0].parameters == {"billId": 1000}
    assert verified["counter_example"]["path_parameter_source"] == "contextual_memory.db whitelist"
    assert verified["counter_example"]["server_actual_response"]["status_code"] == 200
    assert verified["runtime_verdict"] == "STATIC_WIN"


def test_resolver_replaces_llm_literal_path_identifier_with_memory_whitelist(tmp_path):
    endpoint = "get-/bills/{billId}"
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.set_current(endpoint)
    memory.add({"billId": 42})
    memory.close()

    staged = conflict_record()
    record = staged.pop("get-/things")
    record["return.count"]["endpoint"] = endpoint
    record["return.count"]["counter_example"]["staged_payload"]["endpoint_path"] = "/bills/99999"
    staged[endpoint] = record
    requestor = FakeRequestor(parsed={"count": 3})

    ConstraintConflictResolver(cache_dir=tmp_path, requestor=requestor).resolve(staged)

    assert requestor.requests[0].endpoint_path == "/bills/{billId}"
    assert requestor.requests[0].parameters == {"limit": 3, "billId": 42}


def test_resolver_persists_completed_runtime_response_before_later_interrupt(tmp_path):
    data = conflict_record()
    data["get-/other"] = copy.deepcopy(data["get-/things"])
    data["get-/other"]["return.count"]["endpoint"] = "get-/other"

    class InterruptingRequestor(FakeRequestor):
        def exec(self, request):
            if self.requests:
                raise KeyboardInterrupt()
            return super().exec(request)

    with pytest.raises(KeyboardInterrupt):
        ConstraintConflictResolver(
            cache_dir=tmp_path,
            requestor=InterruptingRequestor(parsed={"count": 3}),
        ).resolve(data)

    persisted = json.loads((tmp_path / "combine_constraint_miners.json").read_text("utf-8"))
    response = persisted["get-/things"]["return.count"]["counter_example"][
        "server_actual_response"
    ]
    assert response["status_code"] == 200


def test_rule_evaluator_parses_boolean_list_constraint():
    evaluator = ConstraintRuleEvaluator()

    assert evaluator.evaluate(
        "in(return.items[].isAct, [true, false])",
        "return.items[].isAct",
        {"items": [{"isAct": False}]},
        {},
    )


def test_rule_evaluator_translates_daikon_elements_and_membership():
    evaluator = ConstraintRuleEvaluator()
    expression = (
        "and(return.introducedSessionId == return.currentStage.sessionId,"
        "return.includedSessionIds[] elements == return.introducedSessionId,"
        "return.introducedSessionId in return.includedSessionIds[])"
    )

    assert evaluator.evaluate(
        expression,
        "return.introducedSessionId",
        {
            "introducedSessionId": 20,
            "currentStage": {"sessionId": 20},
            "includedSessionIds": [20],
        },
        {},
        dynamic=True,
    )


def test_rule_evaluator_sizes_existing_empty_response_array():
    evaluator = ConstraintRuleEvaluator()

    assert evaluator.evaluate(
        "return.totalResults >= size(return.items[])",
        "return.totalResults",
        {"items": [], "totalResults": 0},
        {},
        dynamic=True,
    )


def test_resolver_retries_whitelisted_path_value_until_property_is_present(tmp_path):
    endpoint = "get-/bills/{billId}"
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.set_current(endpoint)
    memory.add({"billId": 1000})
    memory.add({"billId": 100})
    memory.close()
    data = {
        endpoint: {
            "return.currentStage.stageSittings[].billId": {
                "endpoint": endpoint,
                "property": "return.currentStage.stageSittings[].billId",
                "static_constraint": "gt(return.currentStage.stageSittings[].billId, 0)",
                "dynamic_constraint": "return.currentStage.stageSittings.billId >= 1",
                "status": "UNRESOLVED",
                "relation": "DYNAMIC_STRONGER",
                "final_constraint": None,
                "reason": "Needs response property.",
                "runtime_verdict": None,
                "counter_example": None,
            }
        }
    }

    class BillRequestor(FakeRequestor):
        def exec(self, request):
            self.requests.append(request)
            bill_id = request.parameters["billId"]
            sittings = [] if bill_id == 1000 else [{"billId": bill_id}]
            return ResponseData(
                status_code=200,
                headers={},
                cookies={},
                mime_type="application/json",
                body="",
                parsed={"currentStage": {"stageSittings": sittings}},
            )

    requestor = BillRequestor()
    record = ConstraintConflictResolver(cache_dir=tmp_path, requestor=requestor).resolve(data)[
        endpoint
    ]["return.currentStage.stageSittings[].billId"]

    assert [request.parameters["billId"] for request in requestor.requests] == [1000, 100]
    assert record["validation_cases"][1]["request"]["parameters"]["billId"] == 100
    assert record["validation_cases"][1]["response_summary"]["status_code"] == 200
    assert record["runtime_verdict"] == "BOTH_TRUE"


def test_rule_evaluator_treats_missing_optional_input_as_false_exists_guard():
    evaluator = ConstraintRuleEvaluator()

    assert evaluator.evaluate(
        "and(gt(return.id,0),implies(exists(input.id),eq(return.id,input.id)))",
        "return.id",
        {"id": 42},
        {},
    )


def test_resolver_prefers_typed_path_parameter_over_string_duplicate(tmp_path):
    endpoint = "get-/bills/{billId}"
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.set_current(endpoint)
    memory.add({"billId": "100"})
    memory.add({"billId": 42})
    memory.close()
    data = conflict_record()
    record = data.pop("get-/things")
    record["return.count"]["endpoint"] = endpoint
    record["return.count"]["counter_example"]["staged_payload"]["parameters"]["billId"] = "100"
    data[endpoint] = record
    requestor = FakeRequestor(parsed={"count": 3})

    ConstraintConflictResolver(cache_dir=tmp_path, requestor=requestor).resolve(data)

    assert requestor.requests[0].parameters["billId"] == 42


def test_resolver_records_configurable_multiple_validation_cases_with_rules(tmp_path):
    endpoint = "get-/things/{id}"
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.set_current(endpoint)
    for value in (1, 2, 3, 4):
        memory.add({"id": value})
    memory.close()
    data = conflict_record()
    record = data.pop("get-/things")
    record["return.count"]["endpoint"] = endpoint
    data[endpoint] = record

    resolver = ConstraintConflictResolver(
        cache_dir=tmp_path,
        requestor=FakeRequestor(parsed={"count": 5}),
        max_test_cases=3,
    )
    result = resolver.resolve(data)[endpoint]["return.count"]

    assert len(result["validation_cases"]) == 3
    assert [case["request"]["parameters"]["id"] for case in result["validation_cases"]] == [
        1,
        2,
        3,
    ]
    assert result["validation_cases"][0]["static_evaluation"] == {
        "source_expression": "gte(return.count, 0)",
        "executed_expression": "gte(return.count, 0)",
        "result": True,
    }
    assert result["validation_cases"][0]["dynamic_evaluation"]["executed_expression"] == (
        "eq(return.count,5)"
    )
    assert result["runtime_evaluation"]["cases_executed"] == 3
    assert result["runtime_verdict"] == "BOTH_TRUE"
    assert result["runtime_recommendation"] == "INCONCLUSIVE"
    assert result["status"] == "UNRESOLVED"
    assert result["final_constraint"] is None


def test_resolver_executes_distinct_llm_staged_payloads_up_to_configured_limit(tmp_path):
    data = conflict_record()
    data["get-/things"]["return.count"]["counter_example"]["staged_payloads"] = [
        {"parameters": {"limit": 3}},
        {"parameters": {"limit": 4}},
        {"parameters": {"limit": 5}},
    ]
    requestor = FakeRequestor(parsed={"count": 5})

    result = ConstraintConflictResolver(
        cache_dir=tmp_path,
        requestor=requestor,
        max_test_cases=2,
    ).resolve(data)["get-/things"]["return.count"]

    assert [case["request"]["parameters"]["limit"] for case in result["validation_cases"]] == [
        3,
        4,
    ]
