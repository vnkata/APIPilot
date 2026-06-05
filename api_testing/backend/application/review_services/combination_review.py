from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
import uuid
try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

import requests
from pydantic import JsonValue

from api_testing.config.config_loader import load_config
from api_testing.backend.domain.errors import ArtifactConflict, InvalidArtifactRequest
from api_testing.backend.domain.models import CombinationDetail
from api_testing.backend.domain.redaction import sanitize_json_value
from api_testing.backend.domain.review_models import (
    CombinationReviewDetail,
    CounterExampleCase,
)
from api_testing.backend.infrastructure.combination_review_metadata import (
    SQLiteCombinationReviewRepository,
)
from api_testing.backend.settings import BackendSettings
from api_testing.backend.application.review_services.counter_example_requests import (
    allowlist_from_spec,
    assert_executable_request_safe,
    merge_validation_errors,
    prepare_counter_example_request,
    resolve_secret_refs,
)
from api_testing.constraint.counter_examples import (
    CounterExampleLLMPlanner,
    build_counter_example_context,
    counter_example_request_to_request_data,
    evaluate_counter_example_runtime_case,
    generate_draft_cases,
    planner_strategy_for_relation,
)
from api_testing.constraint.counter_examples.planner import PROMPT_VERSION
from api_testing.constraint.counter_examples.reducer import reduce_runtime_evidence
from api_testing.prompts.factory import PromptFactory
from api_testing.models.http_data import RequestData, ResponseData


ELIGIBLE_DRAFT_RELATIONS = {
    "STATIC_STRONGER",
    "DYNAMIC_STRONGER",
    "PARTIAL_OVERLAP",
    "DISJOINT",
    "UNKNOWN",
}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CombinationReviewService:
    """Coordinates HITL review state for typed Combination rows."""

    def __init__(
        self,
        artifact_service,
        review_repository: SQLiteCombinationReviewRepository,
        settings: BackendSettings,
        planner_factory: Any | None = None,
    ) -> None:
        self.artifact_service = artifact_service
        self.review_repository = review_repository
        self.settings = settings
        self.planner_factory = planner_factory

    def get_review(self, run_name: str, combination_id: str) -> CombinationReviewDetail:
        detail = self._detail(run_name, combination_id)
        review = self._get_or_create_review(run_name, detail)
        return self._review_detail(review.review_key)

    def generate_counter_examples(
        self,
        run_name: str,
        combination_id: str,
        *,
        live_llm: bool,
        idempotency_key: str,
        max_cases: int | None = None,
    ) -> CombinationReviewDetail:
        detail = self._detail(run_name, combination_id)
        if detail.relation not in ELIGIBLE_DRAFT_RELATIONS:
            raise InvalidArtifactRequest(
                f"Combination entry is not eligible for counter-example drafts: {detail.relation}"
            )
        review = self._get_or_create_review(run_name, detail)
        request_hash = _request_hash(
            {
                "run_name": run_name,
                "combination_id": combination_id,
                "live_llm": live_llm,
                "max_cases": max_cases,
            }
        )
        if self._idempotent_replay(
            review.review_key,
            action="generate",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        ):
            return self._review_detail(review.review_key)

        generation_id = f"ceg_{uuid.uuid4().hex}"
        max_cases_value = max_cases or 3
        drafts = (
            self._live_planner_drafts(
                run_name=run_name,
                detail=detail,
                max_cases=max_cases_value,
            )
            if live_llm
            else [_fallback_draft_case(detail)]
        )[:max_cases_value]
        if not drafts:
            drafts = [
                {
                    "request": _draft_request_from_detail(detail),
                    "target_truth_vector": {
                        "static_constraint": "unknown",
                        "dynamic_constraint": "unknown",
                    },
                    "rationale": "Planner returned no valid draft cases.",
                    "risk": "low",
                    "expected_observation": "No executable planner output was available.",
                    "validation_error": {
                        "error_type": "planner_empty_result",
                        "message": "Planner returned no valid draft cases.",
                    },
                }
            ]
        allowlist = self._request_allowlist(run_name, detail)
        prepared_drafts = [
            _prepare_draft_for_persistence(draft, allowlist=allowlist)
            for draft in drafts
        ]
        self.review_repository.create_draft_cases(
            review_key=review.review_key,
            cases=prepared_drafts,
            source="live_llm" if live_llm else "combination_detail",
            generation_id=generation_id,
            planner_version=(
                str(drafts[0].get("planner_version"))
                if drafts and drafts[0].get("planner_version")
                else (PROMPT_VERSION if live_llm else "fallback-draft-v1")
            ),
            source_metadata={
                "live_llm": live_llm,
                "generation_id": generation_id,
                "max_cases": max_cases_value,
            },
        )
        self.review_repository.record_idempotency(
            review_key=review.review_key,
            action="generate",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_metadata={"generation_id": generation_id},
        )
        self._materialize_sidecar(run_name)
        return self._review_detail(review.review_key)

    def batch_generate_counter_examples(
        self,
        run_name: str,
        combination_ids: list[str],
        *,
        live_llm: bool,
        idempotency_key: str,
        max_items: int | None,
        max_cases_per_item: int | None,
    ) -> list[dict[str, JsonValue]]:
        results: list[dict[str, JsonValue]] = []
        bounded_ids = combination_ids[: min(max_items or len(combination_ids), self.settings.max_counter_example_batch_items)]
        for index, combination_id in enumerate(bounded_ids, start=1):
            try:
                detail = self._detail(run_name, combination_id)
                if detail.relation not in ELIGIBLE_DRAFT_RELATIONS:
                    results.append(
                        {
                            "combination_id": combination_id,
                            "status": "skipped",
                            "case_count": 0,
                            "new_case_count": 0,
                            "total_case_count": 0,
                            "message": "Combination entry is not eligible for draft generation.",
                        }
                    )
                    continue
                review = self._get_or_create_review(run_name, detail)
                before_count = len(self.review_repository.list_cases(review.review_key))
                review_detail = self.generate_counter_examples(
                    run_name,
                    combination_id,
                    live_llm=live_llm,
                    idempotency_key=f"{idempotency_key}:{index}:{combination_id}",
                    max_cases=max_cases_per_item,
                )
                total_count = len(review_detail.cases)
                results.append(
                    {
                        "combination_id": combination_id,
                        "status": "generated",
                        "case_count": total_count,
                        "new_case_count": max(total_count - before_count, 0),
                        "total_case_count": total_count,
                        "message": None,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "combination_id": combination_id,
                        "status": "error",
                        "case_count": 0,
                        "new_case_count": 0,
                        "total_case_count": 0,
                        "message": str(exc),
                    }
                )
        return results

    def update_counter_example_case(
        self,
        run_name: str,
        combination_id: str,
        case_id: str,
        *,
        case_state: str,
        rationale: str | None,
        request: JsonValue | None,
    ) -> CombinationReviewDetail:
        detail = self._detail(run_name, combination_id)
        review = self._get_or_create_review(run_name, detail)
        if case_state not in {"DRAFT", "APPROVED", "REJECTED"}:
            raise InvalidArtifactRequest(f"Unsupported counter-example case_state: {case_state}")
        prepared_request = (
            prepare_counter_example_request(
                request,
                allowlist=self._request_allowlist(run_name, detail),
            )
            if request is not None
            else None
        )
        if case_state == "APPROVED":
            executable_request = (
                prepared_request.request_private
                if prepared_request is not None
                else _existing_case_request(
                    self.review_repository,
                    review.review_key,
                    case_id,
                )
            )
            assert_executable_request_safe(executable_request)
        try:
            self.review_repository.update_case(
                review_key=review.review_key,
                case_id=case_id,
                case_state=case_state,
                rationale=rationale,
                request_private=(
                    prepared_request.request_private if prepared_request else None
                ),
                request_display=(
                    prepared_request.request_display if prepared_request else None
                ),
                validation_error=(
                    prepared_request.validation_error if prepared_request else None
                ),
            )
        except KeyError as exc:
            raise InvalidArtifactRequest(f"Counter-example case not found: {case_id}") from exc
        self._materialize_sidecar(run_name)
        return self._review_detail(review.review_key)

    def run_approved_counter_examples(
        self,
        run_name: str,
        combination_id: str,
        *,
        live_api: bool,
        base_url: str | None,
        request_budget: int,
        timeout_seconds: int,
        unsafe_method_confirmed: bool,
        idempotency_key: str,
    ) -> CombinationReviewDetail:
        detail = self._detail(run_name, combination_id)
        review = self._get_or_create_review(run_name, detail)
        effective_base_url = self._resolve_base_url(run_name, base_url)
        request_hash = _request_hash(
            {
                "run_name": run_name,
                "combination_id": combination_id,
                "live_api": live_api,
                "base_url": effective_base_url,
                "request_budget": request_budget,
                "timeout_seconds": timeout_seconds,
                "unsafe_method_confirmed": unsafe_method_confirmed,
            }
        )
        if self._idempotent_replay(
            review.review_key,
            action="run",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        ):
            return self._review_detail(review.review_key)
        cases = [
            case
            for case in self.review_repository.list_cases(review.review_key)
            if case.case_state == "APPROVED"
        ]
        if not cases:
            raise InvalidArtifactRequest("No approved counter-example cases are available.")
        self._validate_live_run(
            live_api=live_api,
            base_url=effective_base_url,
            request_budget=request_budget,
            timeout_seconds=timeout_seconds,
            cases=cases,
            unsafe_method_confirmed=unsafe_method_confirmed,
        )

        evaluated_cases: list[dict[str, Any]] = []
        for index, case in enumerate(cases, start=1):
            request_data = _request_data_from_case(case)
            response = _execute_request(
                request_data,
                base_url=effective_base_url,
                timeout_seconds=timeout_seconds,
            )
            evaluated = _evaluate_runtime_case(
                run_name=run_name,
                detail=detail,
                request=request_data,
                response=response,
                index=index,
                cache_root=self.settings.cache_root,
            )
            evaluated_cases.append(evaluated)
            self.review_repository.complete_case_run(
                review_key=review.review_key,
                case_id=case.case_id,
                runtime_verdict=str(evaluated["runtime_verdict"]),
                runtime_result=sanitize_json_value(evaluated),
            )
        reduction = reduce_runtime_evidence(
            relation=detail.relation,
            cases=evaluated_cases,
        )
        self.review_repository.set_runtime_recommendation(
            review_key=review.review_key,
            runtime_recommendation=reduction.runtime_recommendation,
        )
        self.review_repository.record_idempotency(
            review_key=review.review_key,
            action="run",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_metadata={"case_count": len(cases)},
        )
        self._materialize_sidecar(run_name)
        return self._review_detail(review.review_key)

    def finalize_review(
        self,
        run_name: str,
        combination_id: str,
        *,
        manual_decision: str,
        idempotency_key: str,
        rationale: str,
        custom_final_constraint: str | None,
    ) -> CombinationReviewDetail:
        detail = self._detail(run_name, combination_id)
        review = self._get_or_create_review(run_name, detail)
        request_hash = _request_hash(
            {
                "run_name": run_name,
                "combination_id": combination_id,
                "manual_decision": manual_decision,
                "rationale": rationale,
                "custom_final_constraint": custom_final_constraint,
            }
        )
        if self._idempotent_replay(
            review.review_key,
            action="finalize",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        ):
            return self._review_detail(review.review_key)
        self.review_repository.finalize_review(
            review_key=review.review_key,
            manual_decision=manual_decision,
            rationale=rationale,
            custom_final_constraint=custom_final_constraint,
        )
        self.review_repository.record_idempotency(
            review_key=review.review_key,
            action="finalize",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_metadata={"manual_decision": manual_decision},
        )
        self._materialize_sidecar(run_name)
        return self._review_detail(review.review_key)

    def reopen_review(
        self,
        run_name: str,
        combination_id: str,
        *,
        rationale: str,
    ) -> CombinationReviewDetail:
        detail = self._detail(run_name, combination_id)
        review = self._get_or_create_review(run_name, detail)
        self.review_repository.reopen_review(
            review_key=review.review_key,
            rationale=rationale,
        )
        self._materialize_sidecar(run_name)
        return self._review_detail(review.review_key)

    def _validate_live_run(
        self,
        *,
        live_api: bool,
        base_url: str,
        request_budget: int,
        timeout_seconds: int,
        cases: list[CounterExampleCase],
        unsafe_method_confirmed: bool,
    ) -> None:
        if not live_api:
            raise InvalidArtifactRequest("counter-example execution requires live_api=true")
        if not self.settings.allowed_target_base_urls:
            raise InvalidArtifactRequest("counter-example execution requires a target base URL allowlist")
        if not any(
            base_url.rstrip("/") == allowed.rstrip("/")
            or base_url.startswith(allowed.rstrip("/") + "/")
            for allowed in self.settings.allowed_target_base_urls
        ):
            raise InvalidArtifactRequest("counter-example base_url is not allowed")
        if request_budget < len(cases):
            raise InvalidArtifactRequest("request_budget is smaller than approved case count")
        if timeout_seconds <= 0:
            raise InvalidArtifactRequest("timeout_seconds must be positive")
        unsafe_methods = {
            str(
                (case.request or {}).get("method")
                or (case.request or {}).get("http_method")
                or "GET"
            ).upper()
            for case in cases
            if str(
                (case.request or {}).get("method")
                or (case.request or {}).get("http_method")
                or "GET"
            ).upper()
            in UNSAFE_METHODS
        }
        if unsafe_methods and not unsafe_method_confirmed:
            methods = ", ".join(sorted(unsafe_methods))
            raise InvalidArtifactRequest(
                f"explicit confirmation is required before executing unsafe method(s): {methods}"
            )

    def _detail(self, run_name: str, combination_id: str) -> CombinationDetail:
        return self.artifact_service.get_combination_entry(run_name, combination_id)

    def _get_or_create_review(
        self,
        run_name: str,
        detail: CombinationDetail,
    ):
        review_key = self.review_repository.review_key_for_detail(run_name, detail)
        return self.review_repository.get_or_create_review(
            run_name=run_name,
            combination_id=detail.combination_id,
            review_key=review_key,
        )

    def _review_detail(self, review_key: str) -> CombinationReviewDetail:
        review = self.review_repository.get_review(review_key)
        return CombinationReviewDetail(
            review=review,
            cases=self.review_repository.list_cases(review_key),
            events=self.review_repository.list_events(review_key),
            target_base_url_suggestions=self._target_base_url_suggestions(
                review.run_name
            ),
        )

    def _resolve_base_url(self, run_name: str, supplied_base_url: str | None) -> str:
        if supplied_base_url and supplied_base_url.strip():
            return supplied_base_url.strip()
        suggestions = self._target_base_url_suggestions(run_name)
        if suggestions:
            return suggestions[0]
        raise InvalidArtifactRequest(
            "counter-example base_url unavailable; provide base_url or regenerate the run with a config/spec server"
        )

    def _target_base_url_suggestions(self, run_name: str) -> list[str]:
        run_dir = self.settings.cache_root / run_name
        candidates: list[str] = []
        configuration = _read_json(run_dir / "configuration.json")
        if isinstance(configuration, dict):
            _append_base_url_candidate(candidates, configuration.get("base_url"))

        config_project = _read_project_config(self.settings.counter_example_planner_config_path)
        if config_project.get("base_title") == run_name:
            _append_base_url_candidate(candidates, config_project.get("base_url"))

        specification = _read_json(run_dir / "specification.json")
        if isinstance(specification, dict):
            servers = specification.get("servers")
            if isinstance(servers, list):
                for server in servers:
                    if isinstance(server, dict):
                        _append_base_url_candidate(candidates, server.get("url"))

        return [
            candidate
            for candidate in _dedupe_urls(candidates)
            if _is_allowed_base_url(candidate, self.settings.allowed_target_base_urls)
        ]

    def _idempotent_replay(
        self,
        review_key: str,
        *,
        action: str,
        idempotency_key: str,
        request_hash: str,
    ) -> bool:
        record = self.review_repository.get_idempotency_record(
            review_key=review_key,
            action=action,
            idempotency_key=idempotency_key,
        )
        if record is None:
            return False
        if record["request_hash"] != request_hash:
            raise ArtifactConflict(
                f"idempotency key conflict for {action}: request body changed"
            )
        return True

    def _live_planner_drafts(
        self,
        *,
        run_name: str,
        detail: CombinationDetail,
        max_cases: int,
    ) -> list[dict[str, JsonValue]]:
        planner = self._planner()
        strategy = planner_strategy_for_relation(detail.relation, planner)
        context = self._planner_context(run_name, detail)
        cases = generate_draft_cases(context, strategy)
        planner_version = getattr(strategy, "prompt_version", None) or PROMPT_VERSION
        drafts: list[dict[str, JsonValue]] = []
        for case in cases[:max_cases]:
            drafts.append(
                {
                    "request": case.request,
                    "target_truth_vector": case.target_truth_vector,
                    "rationale": case.rationale,
                    "risk": case.risk,
                    "expected_observation": case.expected_observation,
                    "validation_error": case.validation_error,
                    "planner_version": planner_version,
                    "source_metadata": {
                        "planner_strategy": getattr(
                            strategy,
                            "strategy_name",
                            context.get("planner_strategy"),
                        ),
                        "source_case_id": case.case_id,
                    },
                }
            )
        if drafts:
            return drafts

        error = getattr(planner, "last_error", None)
        return [
            {
                "request": _draft_request_from_detail(detail),
                "target_truth_vector": {
                    "static_constraint": "unknown",
                    "dynamic_constraint": "unknown",
                },
                "rationale": "Planner did not return a valid draft case.",
                "risk": "low",
                "expected_observation": "No executable planner output was available.",
                "validation_error": sanitize_json_value(
                    error
                    or {
                        "error_type": "planner_empty_result",
                        "message": "Planner returned no valid cases.",
                    }
                ),
                "planner_version": planner_version,
            }
        ]

    def _planner(self):
        if self.planner_factory is not None:
            return self.planner_factory()
        config = load_config(str(self.settings.counter_example_planner_config_path))
        prompt_factory = PromptFactory.from_config(config)
        llm = prompt_factory.get_llm("CounterExampleLLMPlanner")
        if hasattr(llm, "load_model"):
            llm.load_model()
        planner = CounterExampleLLMPlanner(llm=llm)
        planner.prompt_version = PROMPT_VERSION
        return planner

    def _planner_context(
        self,
        run_name: str,
        detail: CombinationDetail,
    ) -> dict[str, JsonValue]:
        run_dir = self.settings.cache_root / run_name
        combination = {
            **detail.raw_record_sanitized,
            "case_id": detail.combination_id,
            "operation_id": detail.operation_id,
            "property_path": detail.property_path,
            "relation": detail.relation,
            "status": detail.status,
            "static_constraint": detail.static_constraint,
            "dynamic_constraint": detail.dynamic_constraint,
            "final_constraint": detail.final_constraint,
            "reason": detail.reason,
            "counter_example": detail.counter_example,
        }
        return build_counter_example_context(
            combination,
            openapi_spec=_read_json(run_dir / "specification.json"),
            reports=_read_json(run_dir / "reports.json"),
            test_cases=_read_json(run_dir / "test_cases.json"),
            contextual_memory=_read_json(run_dir / "contextual_memory.json"),
        )

    def _request_allowlist(
        self,
        run_name: str,
        detail: CombinationDetail,
    ):
        return allowlist_from_spec(
            _read_json(self.settings.cache_root / run_name / "specification.json"),
            detail.operation_id,
        )

    def _materialize_sidecar(self, run_name: str) -> None:
        reviews = self.review_repository.list_reviews_for_run(run_name)
        payload = {
            "run_name": run_name,
            "reviews": {
                key: {
                    "combination_id": review.combination_id,
                    "review_state": review.review_state,
                    "decision_source": review.decision_source,
                    "manual_decision": review.manual_decision,
                    "rationale": review.rationale,
                    "custom_final_constraint": review.custom_final_constraint,
                    "runtime_recommendation": review.runtime_recommendation,
                    "cases": [
                        {
                            "case_id": case.case_id,
                            "case_state": case.case_state,
                            "request": sanitize_json_value(
                                case.request_display or case.request
                            ),
                            "request_display": sanitize_json_value(
                                case.request_display or case.request
                            ),
                            "source": case.source,
                            "rationale": case.rationale,
                            "generation_id": case.generation_id,
                            "target_truth_vector": sanitize_json_value(case.target_truth_vector),
                            "risk": case.risk,
                            "expected_observation": case.expected_observation,
                            "validation_error": sanitize_json_value(case.validation_error),
                            "planner_version": case.planner_version,
                            "source_metadata": sanitize_json_value(case.source_metadata),
                            "runtime_verdict": case.runtime_verdict,
                            "runtime_result": sanitize_json_value(case.runtime_result),
                        }
                        for case in self.review_repository.list_cases(key)
                    ],
                }
                for key, review in sorted(reviews.items())
            },
        }
        path = self.settings.cache_root / run_name / "counter_example_reviews.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(sanitize_json_value(payload), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _draft_request_from_detail(detail: CombinationDetail) -> dict[str, JsonValue]:
    payload = {}
    if isinstance(detail.counter_example, dict):
        payload = detail.counter_example.get("staged_payload") or {}
    method, _, path = detail.operation_id.partition("-")
    return {
        "method": payload.get("http_method") or method or "get",
        "path": payload.get("endpoint_path") or path or "/",
        "path_parameters": {},
        "query": payload.get("parameters") or {},
        "headers": payload.get("headers") or {},
        "body": payload.get("body"),
    }


def _fallback_draft_case(detail: CombinationDetail) -> dict[str, JsonValue]:
    return {
        "request": _draft_request_from_detail(detail),
        "target_truth_vector": {
            "static_constraint": "unknown",
            "dynamic_constraint": "unknown",
        },
        "rationale": "Deterministic fallback draft from the existing combination detail.",
        "risk": "low",
        "expected_observation": "Reviewer can execute this request to collect runtime support.",
        "planner_version": "fallback-draft-v1",
    }


def _prepare_draft_for_persistence(
    draft: dict[str, JsonValue],
    *,
    allowlist,
) -> dict[str, JsonValue]:
    prepared = prepare_counter_example_request(
        draft.get("request"),
        allowlist=allowlist,
    )
    return {
        **draft,
        "request_private": prepared.request_private,
        "request_display": prepared.request_display,
        "validation_error": merge_validation_errors(
            draft.get("validation_error"),
            prepared.validation_error,
        ),
    }


def _request_data_from_case(case: CounterExampleCase) -> RequestData:
    request = case.request if isinstance(case.request, dict) else {}
    assert_executable_request_safe(request)
    resolved_request = resolve_secret_refs(request)
    if not isinstance(resolved_request, dict):
        raise InvalidArtifactRequest("counter-example request must be an object")
    return counter_example_request_to_request_data(resolved_request)


def _existing_case_request(
    review_repository: SQLiteCombinationReviewRepository,
    review_key: str,
    case_id: str,
) -> JsonValue:
    for case in review_repository.list_cases(review_key):
        if case.case_id == case_id:
            return case.request
    raise InvalidArtifactRequest(f"Counter-example case not found: {case_id}")


def _execute_request(
    request: RequestData,
    *,
    base_url: str,
    timeout_seconds: int,
) -> ResponseData:
    parameters = dict(request.parameters or {})
    endpoint_path = request.endpoint_path
    url = f"{base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
    kwargs: dict[str, Any] = {
        "headers": request.resolve_headers(),
        "cookies": request.resolve_cookies(),
        "params": parameters,
        "timeout": (5.0, float(timeout_seconds)),
    }
    if request.body is not None:
        if "application/json" in request.mime_type:
            kwargs["json"] = request.body
        else:
            kwargs["data"] = request.body
    try:
        return ResponseData.from_requests(
            requests.request(request.http_method.lower(), url, **kwargs)
        )
    except requests.exceptions.RequestException:
        return ResponseData.from_requests(None)


def _evaluate_runtime_case(
    *,
    run_name: str,
    detail: CombinationDetail,
    request: RequestData,
    response: ResponseData,
    index: int,
    cache_root: Path,
) -> dict[str, Any]:
    return evaluate_counter_example_runtime_case(
        run_name=run_name,
        detail=detail,
        request=request,
        response=response,
        index=index,
        cache_root=cache_root,
    )


def _request_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> JsonValue | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except Exception:
        return None


def _read_project_config(path: Path) -> dict[str, str]:
    try:
        with Path(path).open("rb") as fh:
            raw = tomllib.load(fh)
    except Exception:
        return {}
    project = raw.get("project")
    if not isinstance(project, dict):
        return {}
    return {
        "base_title": str(project.get("base_title") or ""),
        "base_url": str(project.get("base_url") or ""),
    }


def _append_base_url_candidate(candidates: list[str], value: Any) -> None:
    if isinstance(value, str) and value.strip():
        candidates.append(value.strip())


def _dedupe_urls(candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    for candidate in candidates:
        normalized = candidate.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        values.append(candidate)
    return values


def _is_allowed_base_url(
    base_url: str,
    allowed_target_base_urls: tuple[str, ...],
) -> bool:
    if not allowed_target_base_urls:
        return True
    return any(
        base_url.rstrip("/") == allowed.rstrip("/")
        or base_url.startswith(allowed.rstrip("/") + "/")
        for allowed in allowed_target_base_urls
    )
