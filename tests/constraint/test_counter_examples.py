from api_testing.constraint.counter_examples import (
    ApprovedCounterExampleCase,
    CounterExampleLLMPlanner,
    CounterExamplePlannerResponse,
    build_counter_example_context,
    counter_example_request_to_request_data,
    evaluate_counter_example_runtime_case,
    generate_draft_cases,
    planner_strategy_for_relation,
    reduce_runtime_evidence,
    run_approved_cases,
)


class FakeDraftProvider:
    def __init__(self):
        self.contexts = []

    def generate(self, context):
        self.contexts.append(context)
        return [
            {
                "case_id": "case-1",
                "rationale": "Probe the dynamic-only branch.",
                "request": {"method": "GET", "path": "/items", "query": {"limit": 0}},
            },
            {"case_id": "ignored", "rationale": "Missing request"},
        ]


class FakeExecutor:
    def __init__(self):
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        return {
            "runtime_result": {"status_code": 200},
            "runtime_verdict": "BOTH_TRUE",
        }


def test_counter_example_context_uses_combination_identity_fields():
    context = build_counter_example_context(
        {
            "operation_id": "get-/items",
            "property_path": "return.items[].id",
            "relation": "DYNAMIC_STRONGER",
            "status": "UNRESOLVED",
            "static_constraint": "exists(return.items[].id)",
            "dynamic_constraint": "return.items[].id >= 1",
        }
    )

    assert context["operation_id"] == "get-/items"
    assert context["property_path"] == "return.items[].id"
    assert context["relation"] == "DYNAMIC_STRONGER"


def test_counter_example_context_sanitizes_and_bounds_supporting_artifacts():
    context = build_counter_example_context(
        {
            "operation_id": "post-/items",
            "property_path": "return.id",
            "relation": "PARTIAL_OVERLAP",
            "status": "UNRESOLVED",
            "static_constraint": "exists(return.id)",
            "dynamic_constraint": "return.id >= 1",
        },
        openapi_spec={
            "paths": {
                "/items": {
                    "post": {
                        "operationId": "createItem",
                        "parameters": [
                            {"name": "Authorization", "in": "header"},
                            {"name": "category", "in": "query"},
                        ],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "api_key": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                    }
                }
            }
        },
        reports=[
            {
                "operation_id": "post-/items",
                "Authorization": "Bearer secret-token",
                "message": "A" * 200,
            }
        ],
        test_cases=[
            {
                "request": {
                    "headers": {"x-api-key": "secret-token"},
                    "body": {"name": "ok"},
                }
            }
        ],
        contextual_memory={
            "contexts": {
                "post-/items": {
                    "whitelist": [{"category": "books", "password": "secret"}]
                }
            }
        },
        max_items=1,
        max_text_length=48,
    )

    rendered = str(context)
    assert "secret-token" not in rendered
    assert "password': 'secret" not in rendered
    assert "A" * 80 not in rendered
    assert context["operation"]["method"] == "post"
    assert context["operation"]["path"] == "/items"
    assert context["operation"]["parameters"] == [
        {"name": "Authorization", "in": "header"},
        {"name": "category", "in": "query"},
    ]
    assert context["reports_summary"][0]["Authorization"] == "<REDACTED>"


def test_draft_generator_calls_provider_and_skips_malformed_cases():
    provider = FakeDraftProvider()
    context = {"operation_id": "get-/items", "relation": "UNKNOWN"}

    cases = generate_draft_cases(context, provider)

    assert provider.contexts == [context]
    assert len(cases) == 1
    assert cases[0].case_id == "case-1"
    assert cases[0].request["path"] == "/items"
    assert cases[0].target_truth_vector == {
        "static_constraint": "unknown",
        "dynamic_constraint": "unknown",
    }


def test_draft_generator_validates_required_planner_fields():
    class Provider:
        def generate(self, context):
            return [
                {
                    "case_id": "valid",
                    "request": {"method": "GET", "path": "/items"},
                    "target_truth_vector": {
                        "static_constraint": "true",
                        "dynamic_constraint": "false",
                    },
                    "rationale": "Exercise the static-only branch.",
                    "risk": "low",
                    "expected_observation": "The response satisfies only static.",
                },
                {
                    "case_id": "missing-target",
                    "request": {"method": "GET", "path": "/items"},
                    "rationale": "Malformed.",
                    "risk": "low",
                    "expected_observation": "Ignored.",
                },
            ]

    cases = generate_draft_cases({"operation_id": "get-/items"}, Provider())

    assert [case.case_id for case in cases] == ["valid"]
    assert cases[0].target_truth_vector == {
        "static_constraint": "true",
        "dynamic_constraint": "false",
    }
    assert cases[0].risk == "low"
    assert cases[0].expected_observation == "The response satisfies only static."


def test_relation_specific_planner_strategy_classes_add_diagnostic_intent():
    class Planner:
        prompt_version = "fake-v1"

        def __init__(self):
            self.contexts = []

        def generate(self, context):
            self.contexts.append(context)
            return []

    expected = {
        "STATIC_STRONGER": "static_stronger_diagnostic",
        "DYNAMIC_STRONGER": "dynamic_stronger_diagnostic",
        "PARTIAL_OVERLAP": "partial_overlap_diagnostic",
        "DISJOINT": "disjoint_diagnostic",
        "UNKNOWN": "unknown_diagnostic",
        "EQUIVALENT": "generic_diagnostic",
    }
    for relation, strategy_name in expected.items():
        planner = Planner()
        strategy = planner_strategy_for_relation(relation, planner)

        assert strategy.__class__.__name__ != "CounterExamplePlannerStrategy"
        strategy.generate({"relation": relation})

        assert planner.contexts[0]["planner_strategy"] == strategy_name
        assert planner.contexts[0]["planner_strategy_guidance"]


def test_planner_request_adapter_substitutes_path_parameters_and_query():
    request = counter_example_request_to_request_data(
        {
            "method": "GET",
            "path": "/items/{itemId}",
            "path_parameters": {"itemId": 42},
            "query": {"include": "details"},
            "headers": {"x-safe": "ok"},
            "body": None,
        }
    )

    assert request.endpoint_path == "/items/42"
    assert request.http_method == "GET"
    assert request.parameters == {"include": "details"}
    assert request.headers == {"x-safe": "ok"}


def test_planner_request_adapter_rejects_unresolved_templates():
    try:
        counter_example_request_to_request_data(
            {"method": "GET", "path": "/items/{itemId}", "query": {}}
        )
    except ValueError as exc:
        assert "unresolved path parameter" in str(exc)
    else:
        raise AssertionError("Expected unresolved path template to be rejected.")


def test_public_runtime_evaluator_returns_sanitized_verdict(tmp_path):
    from api_testing.backend.domain.models import CombinationDetail
    from api_testing.models.http_data import ResponseData

    detail = CombinationDetail(
        combination_id="combination-1",
        operation_id="get-/items",
        property_path="return.item_count",
        status="UNRESOLVED",
        relation="DYNAMIC_STRONGER",
        runtime_verdict=None,
        resolved=False,
        static_constraint="gte(return.item_count, 0)",
        dynamic_constraint="return.item_count == 5",
        final_constraint=None,
        reason_preview="Needs evidence",
        has_counter_example=True,
        has_runtime_evaluation=False,
        validation_case_count=0,
        source_artifact="combine_constraint_miners",
        review_state="PENDING_REVIEW",
        decision_source=None,
        has_manual_decision=False,
        reason="Needs evidence",
        counter_example=None,
        runtime_evaluation=None,
        validation_cases=[],
        raw_record_sanitized={},
    )

    result = evaluate_counter_example_runtime_case(
        run_name="Run A",
        detail=detail,
        request=counter_example_request_to_request_data(
            {"method": "GET", "path": "/items", "query": {}}
        ),
        response=ResponseData(
            status_code=200,
            headers={"Content-Type": "application/json"},
            cookies={},
            mime_type="application/json",
            body='{"item_count": 5, "access_token": "secret"}',
            parsed={"item_count": 5, "access_token": "secret"},
            encoding="utf-8",
        ),
        index=1,
        cache_root=tmp_path,
    )

    assert result["runtime_verdict"] == "BOTH_TRUE"
    assert "secret" not in str(result)


class FlakyPlannerLLM:
    def __init__(self):
        self.prompts = []

    def generate(self, **kwargs):
        self.prompts.append(kwargs["prompt"])
        if len(self.prompts) == 1:
            raise ValueError("JSON parse failed")
        return (
            CounterExamplePlannerResponse(
                cases=[
                    {
                        "case_id": "repair-case",
                        "request": {"method": "GET", "path": "/items"},
                        "target_truth_vector": {
                            "static_constraint": "true",
                            "dynamic_constraint": "false",
                        },
                        "rationale": "Probe static-only evidence.",
                        "risk": "low",
                        "expected_observation": "Static true and dynamic false.",
                    }
                ]
            ),
            0,
        )


def test_llm_planner_retries_once_and_records_repair_attempt():
    llm = FlakyPlannerLLM()
    planner = CounterExampleLLMPlanner(llm=llm)

    raw_cases = planner.generate(
        {
            "case_id": "gold-static-only",
            "operation_id": "get-/items",
            "property_path": "return.id",
            "relation": "DYNAMIC_STRONGER",
            "static_constraint": "exists(return.id)",
            "dynamic_constraint": "return.id >= 1",
        }
    )

    assert raw_cases[0]["case_id"] == "repair-case"
    assert len(llm.prompts) == 2
    assert "Previous structured output error" in llm.prompts[1]
    assert planner.last_error is None
    assert planner.last_interactions[0]["error"] == "JSON parse failed"
    assert planner.last_interactions[1]["parsed_response"]["cases"][0]["case_id"] == (
        "repair-case"
    )


def test_llm_planner_records_structured_error_after_retry_failure():
    class BrokenLLM:
        def generate(self, **kwargs):
            raise ValueError("still invalid")

    planner = CounterExampleLLMPlanner(llm=BrokenLLM())

    assert planner.generate({"case_id": "bad"}) == []
    assert planner.last_error == {
        "error_type": "planner_parse_error",
        "message": "still invalid",
    }
    assert len(planner.last_interactions) == 2


def test_runner_executes_approved_cases_only_through_executor():
    executor = FakeExecutor()

    results = run_approved_cases(
        [
            ApprovedCounterExampleCase(
                case_id="case-1",
                request={"method": "GET", "path": "/items"},
            )
        ],
        executor,
    )

    assert executor.requests == [{"method": "GET", "path": "/items"}]
    assert results[0].case_id == "case-1"
    assert results[0].runtime_verdict == "BOTH_TRUE"


def test_reducer_never_turns_runtime_support_into_final_decision():
    reduction = reduce_runtime_evidence(
        relation="DYNAMIC_STRONGER",
        cases=[{"runtime_verdict": "BOTH_TRUE"}],
    )

    assert reduction.runtime_verdict == "BOTH_TRUE"
    assert reduction.runtime_recommendation == "INCONCLUSIVE"
