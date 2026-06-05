"""Automated research run for counter-example evidence and CSV labels."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable
from urllib.parse import urljoin

import requests

from api_testing.config.config_loader import load_config
from api_testing.constraint.counter_examples import (
    CounterExampleLLMPlanner,
    build_counter_example_context,
    counter_example_request_to_request_data,
    evaluate_counter_example_runtime_case,
    generate_draft_cases,
    planner_strategy_for_relation,
    reduce_runtime_evidence,
)
from api_testing.constraint.research_artifacts import (
    CASE_EVIDENCE_FILENAME,
    LABEL_FILENAME,
    SUMMARY_FILENAME,
    ResearchCaseEvidence,
    ResearchPairLabel,
    load_case_evidence,
    load_pair_labels,
    research_pair_id,
    suggested_labels_for_runtime,
    summarize_research_artifacts,
    utc_now_iso,
    write_case_evidence,
    write_pair_labels_atomic,
)
from api_testing.models.http_data import ResponseData
from api_testing.prompts.factory import PromptFactory


@dataclass(frozen=True, slots=True)
class ResearchAutomationConfig:
    counter_examples_per_pair: int = 5
    live_planner: bool = False
    planner_config_path: str = "configurations.toml"
    allow_non_get: bool = False
    confirm_unsafe_methods: bool = False
    target_base_url: str | None = None
    allowed_target_base_urls: tuple[str, ...] = ()
    request_budget: int = 5
    timeout_seconds: float = 10.0
    overwrite_labels_with_backup: bool = False
    overwrite_evidence: bool = False


@dataclass(frozen=True, slots=True)
class ResearchAutomationResult:
    output_dir: Path
    labels_path: Path
    evidence_path: Path
    summary_path: Path
    summary: dict[str, Any]


Executor = Callable[[dict[str, Any]], dict[str, Any]]
PlannerFactory = Callable[[], Any]


def run_research_automation(
    cache_dir: str | Path,
    config: ResearchAutomationConfig,
    *,
    run_id: str | None = None,
    executor: Executor | None = None,
    planner_factory: PlannerFactory | None = None,
) -> ResearchAutomationResult:
    run_dir = Path(cache_dir)
    if not run_dir.exists():
        raise FileNotFoundError(f"Cache directory does not exist: {run_dir}")
    run_id = run_id or _timestamp_compact()
    output_dir = run_dir / "research_runs" / run_id
    if output_dir.exists():
        raise FileExistsError(f"Research run output already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    pairs = _load_research_pairs(run_dir)
    if pairs:
        base_url = _resolve_base_url(run_dir, config)
        if not base_url:
            raise ValueError("Research automation requires a target base URL.")
        if config.allowed_target_base_urls and not any(
            base_url.startswith(allowed) for allowed in config.allowed_target_base_urls
        ):
            raise ValueError("Target base URL is not in the allowlist.")
    else:
        base_url = None

    case_budget = max(1, config.counter_examples_per_pair)
    if pairs and config.request_budget < len(pairs) * case_budget:
        raise ValueError("Request budget is lower than generated case count.")

    executor = executor or _requests_executor(base_url or "", config.timeout_seconds)
    labels_path = run_dir / LABEL_FILENAME
    evidence_path = run_dir / CASE_EVIDENCE_FILENAME
    previous_labels = [] if config.overwrite_labels_with_backup else load_pair_labels(labels_path)
    previous_by_pair_id = {item.research_pair_id: item for item in previous_labels}
    previous_by_combination_id = {item.combination_id: item for item in previous_labels}
    active_pair_ids: set[str] = set()
    labels: list[ResearchPairLabel] = []
    evidence: list[ResearchCaseEvidence] = []
    for pair in pairs:
        active_pair_ids.add(pair["research_pair_id"])
        pair_evidence: list[ResearchCaseEvidence] = []
        drafts = _draft_cases_for_pair(
            pair,
            run_dir=run_dir,
            config=config,
            case_budget=case_budget,
            planner_factory=planner_factory,
        )
        for index, draft in enumerate(drafts, start=1):
            request = draft["request"]
            invalid_reason = _invalid_reason_for_request(request, config)
            invalid_detail = ""
            runtime_verdict = ""
            runtime_recommendation = "INCONCLUSIVE"
            response_summary: dict[str, Any] = {}
            if invalid_reason:
                invalid_detail = _invalid_detail_for_reason(invalid_reason, request)
                response_summary = {}
            else:
                execution = executor(request)
                execution_invalid_reason = _execution_invalid_reason(execution)
                if execution_invalid_reason:
                    invalid_reason = execution_invalid_reason
                    invalid_detail = _invalid_detail_for_reason(invalid_reason, request)
                    response_summary = _sanitize_summary(
                        execution.get("runtime_result") or {}
                    )
                else:
                    runtime_verdict, runtime_recommendation, response_summary = (
                        _runtime_evidence_from_execution(
                            pair=pair,
                            request=request,
                            execution=execution,
                            index=index,
                            run_dir=run_dir,
                        )
                    )
            item = ResearchCaseEvidence(
                pair_id=pair["research_pair_id"],
                combination_id=pair["combination_id"],
                case_id=f"{pair['research_pair_id']}-case-{index}",
                request_summary=_sanitize_summary(request),
                response_summary=response_summary,
                runtime_verdict=runtime_verdict,
                runtime_recommendation=runtime_recommendation,
                invalid_reason=invalid_reason,
                invalid_detail=invalid_detail,
                planner_status=str(draft.get("planner_status") or "fallback"),
                planner_error_kind=str(draft.get("planner_error_kind") or ""),
                weak_evidence=bool(draft.get("weak_evidence", False)),
                execution_metadata={
                    "index": index,
                    "run_id": run_id,
                    "planner_version": draft.get("planner_version"),
                    "planner_strategy": draft.get("planner_strategy"),
                },
            )
            evidence.append(item)
            pair_evidence.append(item)

        pair_recommendation = _last_recommendation(pair_evidence)
        suggested_static, suggested_dynamic, suggested_combined = (
            suggested_labels_for_runtime(pair_recommendation)
        )
        existing_label = previous_by_pair_id.get(
            pair["research_pair_id"]
        ) or previous_by_combination_id.get(pair["combination_id"])
        refreshed_label = ResearchPairLabel(
            run_name=run_dir.name,
            research_pair_id=pair["research_pair_id"],
            combination_id=pair["combination_id"],
            operation_id=pair["operation_id"],
            property_path=pair["property_path"],
            relation=pair["relation"],
            status=pair["status"],
            static_constraint=pair["static_constraint"],
            dynamic_constraint=pair["dynamic_constraint"],
            final_constraint=pair["final_constraint"] or "",
            runtime_recommendation=pair_recommendation,
            suggested_static_label=suggested_static,
            suggested_dynamic_label=suggested_dynamic,
            suggested_combined_label=suggested_combined,
            static_label=existing_label.static_label if existing_label else "UNSURE",
            dynamic_label=existing_label.dynamic_label if existing_label else "UNSURE",
            combined_label=existing_label.combined_label if existing_label else "",
            notes=existing_label.notes if existing_label else "",
            updated_at=existing_label.updated_at if existing_label else utc_now_iso(),
            orphaned=False,
        )
        labels.append(refreshed_label)

    for previous in previous_labels:
        if previous.research_pair_id in active_pair_ids:
            continue
        labels.append(
            ResearchPairLabel(
                run_name=run_dir.name,
                research_pair_id=previous.research_pair_id,
                combination_id=previous.combination_id,
                operation_id=previous.operation_id,
                property_path=previous.property_path,
                relation=previous.relation,
                status=previous.status,
                static_constraint=previous.static_constraint,
                dynamic_constraint=previous.dynamic_constraint,
                final_constraint=previous.final_constraint,
                runtime_recommendation=previous.runtime_recommendation,
                suggested_static_label=previous.suggested_static_label,
                suggested_dynamic_label=previous.suggested_dynamic_label,
                suggested_combined_label=previous.suggested_combined_label,
                static_label=previous.static_label,
                dynamic_label=previous.dynamic_label,
                combined_label=previous.combined_label,
                notes=previous.notes,
                updated_at=previous.updated_at,
                orphaned=True,
            )
        )

    if evidence_path.exists() and not config.overwrite_evidence:
        evidence = [*load_case_evidence(evidence_path), *evidence]
    write_pair_labels_atomic(labels_path, labels)
    write_case_evidence(evidence_path, evidence)
    summary = summarize_research_artifacts(labels, evidence)
    summary.update(
        {
            "run_name": run_dir.name,
            "run_id": run_id,
            "label_artifact": LABEL_FILENAME,
            "evidence_artifact": CASE_EVIDENCE_FILENAME,
            "counter_examples_per_pair": case_budget,
            "config": {
                "counter_examples_per_pair": case_budget,
                "live_planner": config.live_planner,
                "allow_non_get": config.allow_non_get,
                "confirm_unsafe_methods": config.confirm_unsafe_methods,
                "request_budget": config.request_budget,
                "timeout_seconds": config.timeout_seconds,
                "target_base_url_provided": bool(config.target_base_url),
                "allowed_target_base_url_count": len(config.allowed_target_base_urls),
                "planner_config_path": config.planner_config_path,
                "overwrite_labels_with_backup": config.overwrite_labels_with_backup,
                "overwrite_evidence": config.overwrite_evidence,
            },
        }
    )
    summary_path = output_dir / SUMMARY_FILENAME
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    shutil.copy2(labels_path, output_dir / LABEL_FILENAME)
    shutil.copy2(evidence_path, output_dir / CASE_EVIDENCE_FILENAME)
    return ResearchAutomationResult(
        output_dir=output_dir,
        labels_path=labels_path,
        evidence_path=evidence_path,
        summary_path=summary_path,
        summary=summary,
    )


def main() -> None:
    args = _parse_args()
    config = _config_from_args(args)
    result = run_research_automation(
        args.cache_dir,
        config,
        run_id=args.run_id,
    )
    print(
        json.dumps(
            {"output_dir": str(result.output_dir), **result.summary}, sort_keys=True
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run APIPilot counter-example research automation."
    )
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--config", default="configurations.toml")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--counter-examples-per-pair", type=int, default=None)
    parser.add_argument("--live-planner", action="store_true")
    parser.add_argument("--allow-non-get", action="store_true")
    parser.add_argument("--confirm-unsafe-methods", action="store_true")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--allowed-base-url", action="append", default=None)
    parser.add_argument("--request-budget", type=int, default=None)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--overwrite-labels-with-backup", action="store_true")
    parser.add_argument("--overwrite-evidence", action="store_true")
    return parser.parse_args()


def _config_from_args(args: argparse.Namespace) -> ResearchAutomationConfig:
    file_config = _load_research_config(Path(args.config))
    return ResearchAutomationConfig(
        counter_examples_per_pair=args.counter_examples_per_pair
        or int(file_config.get("counter_examples_per_pair", 5)),
        live_planner=bool(args.live_planner or file_config.get("live_planner", False)),
        planner_config_path=str(args.config),
        allow_non_get=bool(
            args.allow_non_get or file_config.get("allow_non_get", False)
        ),
        confirm_unsafe_methods=bool(
            args.confirm_unsafe_methods
            or file_config.get("confirm_unsafe_methods", False)
        ),
        target_base_url=args.base_url or file_config.get("target_base_url"),
        allowed_target_base_urls=tuple(
            args.allowed_base_url or file_config.get("allowed_target_base_urls", ())
        ),
        request_budget=args.request_budget or int(file_config.get("request_budget", 5)),
        timeout_seconds=args.timeout_seconds
        or float(file_config.get("timeout_seconds", 10.0)),
        overwrite_labels_with_backup=bool(
            args.overwrite_labels_with_backup
            or file_config.get("overwrite_labels_with_backup", False)
        ),
        overwrite_evidence=bool(
            args.overwrite_evidence or file_config.get("overwrite_evidence", False)
        ),
    )


def _load_research_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    research = data.get("constraint_research")
    counter_examples = data.get("counter_examples")
    merged: dict[str, Any] = {}
    if isinstance(research, dict):
        merged.update(research)
    if isinstance(counter_examples, dict):
        merged.update(counter_examples)
    return merged


def _load_research_pairs(run_dir: Path) -> list[dict[str, Any]]:
    combine_path = run_dir / "combine_constraint_miners.json"
    if not combine_path.exists():
        raise FileNotFoundError(f"Missing combine artifact: {combine_path}")
    raw = json.loads(combine_path.read_text(encoding="utf-8"))
    pairs: list[dict[str, Any]] = []
    for endpoint, properties in sorted((raw or {}).items()):
        if not isinstance(properties, dict):
            continue
        for property_path, record in sorted(properties.items()):
            if not isinstance(record, dict):
                continue
            relation = record.get("relation")
            static_constraint = record.get("static_constraint")
            dynamic_constraint = record.get("dynamic_constraint")
            if (
                not relation
                or relation == "EQUIVALENT"
                or static_constraint is None
                or dynamic_constraint is None
            ):
                continue
            status = str(record.get("status") or "")
            final_constraint = record.get("final_constraint")
            pair = {
                "operation_id": str(record.get("endpoint") or endpoint),
                "property_path": str(record.get("property") or property_path),
                "status": status,
                "relation": str(relation),
                "static_constraint": str(static_constraint),
                "dynamic_constraint": str(dynamic_constraint),
                "final_constraint": str(final_constraint) if final_constraint else "",
            }
            pair["combination_id"] = _combination_id(pair)
            pair["research_pair_id"] = research_pair_id(
                run_name=run_dir.name,
                operation_id=pair["operation_id"],
                property_path=pair["property_path"],
                static_constraint=pair["static_constraint"],
                dynamic_constraint=pair["dynamic_constraint"],
            )
            pairs.append(pair)
    return pairs


def _resolve_base_url(run_dir: Path, config: ResearchAutomationConfig) -> str | None:
    if config.target_base_url:
        return config.target_base_url
    for filename in (
        "configuration.json",
        "baseline_specification.json",
        "specification.json",
    ):
        path = run_dir / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            project = data.get("project")
            if isinstance(project, dict) and project.get("base_url"):
                return str(project["base_url"])
            servers = data.get("servers")
            if isinstance(servers, list) and servers:
                server = servers[0]
                if isinstance(server, dict) and server.get("url"):
                    return str(server["url"])
    return None


def _draft_cases_for_pair(
    pair: dict[str, Any],
    *,
    run_dir: Path,
    config: ResearchAutomationConfig,
    case_budget: int,
    planner_factory: PlannerFactory | None,
) -> list[dict[str, Any]]:
    if not config.live_planner:
        return [
            _fallback_draft(pair, index, run_dir=run_dir, planner_status="fallback")
            for index in range(1, case_budget + 1)
        ]

    planner_status = "generated"
    planner_error_kind = ""
    planner_version = ""
    planner_strategy = ""
    drafts: list[dict[str, Any]] = []
    try:
        planner = planner_factory() if planner_factory else _planner_from_config(config)
        strategy = planner_strategy_for_relation(pair["relation"], planner)
        planner_version = str(getattr(strategy, "prompt_version", "") or "")
        planner_strategy = str(getattr(strategy, "strategy_name", "") or "")
        context = build_counter_example_context(
            {
                **pair,
                "endpoint": pair["operation_id"],
                "property": pair["property_path"],
                "case_id": pair["research_pair_id"],
            },
            openapi_spec=(
                _read_json(run_dir / "specification.json")
                or _read_json(run_dir / "baseline_specification.json")
            ),
            reports=_read_json(run_dir / "reports.json"),
            test_cases=_read_json(run_dir / "test_cases.json"),
            contextual_memory=_read_json(run_dir / "contextual_memory.json"),
        )
        cases = generate_draft_cases(context, strategy)
        for case in cases[:case_budget]:
            drafts.append(
                {
                    "request": case.request,
                    "target_truth_vector": case.target_truth_vector,
                    "rationale": case.rationale,
                    "risk": case.risk,
                    "expected_observation": case.expected_observation,
                    "planner_status": planner_status,
                    "planner_error_kind": planner_error_kind,
                    "planner_version": planner_version,
                    "planner_strategy": planner_strategy,
                    "weak_evidence": False,
                }
            )
        if len(drafts) >= case_budget:
            return drafts
        planner_error = getattr(planner, "last_error", None)
        if isinstance(planner_error, dict) and planner_error.get("error_type"):
            planner_status = "failed"
            planner_error_kind = str(planner_error.get("error_type") or "planner_error")
        else:
            planner_status = "fallback"
            planner_error_kind = "insufficient_planner_cases"
    except Exception as exc:
        planner_status = "failed"
        planner_error_kind = _planner_error_kind(exc)
        planner_version = planner_version or "unknown"

    for index in range(len(drafts) + 1, case_budget + 1):
        drafts.append(
            _fallback_draft(
                pair,
                index,
                run_dir=run_dir,
                planner_status=planner_status,
                planner_error_kind=planner_error_kind,
                planner_version=planner_version,
                planner_strategy=planner_strategy,
            )
        )
    return drafts


def _planner_from_config(config: ResearchAutomationConfig) -> CounterExampleLLMPlanner:
    loaded = load_config(config.planner_config_path)
    prompt_factory = PromptFactory.from_config(loaded)
    llm = prompt_factory.get_llm("CounterExampleLLMPlanner")
    if hasattr(llm, "load_model"):
        llm.load_model()
    planner = CounterExampleLLMPlanner(llm=llm)
    planner.prompt_version = getattr(planner, "prompt_version", None) or "counter-example-planner-v1"
    return planner


def _fallback_draft(
    pair: dict[str, Any],
    index: int,
    *,
    run_dir: Path,
    planner_status: str,
    planner_error_kind: str = "",
    planner_version: str = "fallback-draft-v1",
    planner_strategy: str = "deterministic_fallback",
) -> dict[str, Any]:
    return {
        "request": _default_request(pair, index, run_dir=run_dir),
        "target_truth_vector": {
            "static_constraint": "unknown",
            "dynamic_constraint": "unknown",
        },
        "rationale": "Deterministic fallback research request.",
        "risk": "low",
        "expected_observation": "Collect runtime support for researcher labeling.",
        "planner_status": planner_status,
        "planner_error_kind": planner_error_kind,
        "planner_version": planner_version,
        "planner_strategy": planner_strategy,
        "weak_evidence": planner_status != "generated",
    }


def _planner_error_kind(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return "planner_validation_error"
    return type(exc).__name__


def _default_request(
    pair: dict[str, Any],
    index: int,
    *,
    run_dir: Path | None = None,
) -> dict[str, Any]:
    method, path = _method_path(pair["operation_id"])
    if run_dir is not None:
        path = (
            _path_from_successful_test_case(pair, method, path, run_dir)
            or _path_from_openapi_defaults(pair, method, path, run_dir)
            or path
        )
    return {
        "method": method,
        "path": path,
        "query": {"research_case": index},
        "headers": {},
        "body": None,
        "target_truth_vector": {
            "static_constraint": "unknown",
            "dynamic_constraint": "unknown",
        },
    }


def _method_path(operation_id: str) -> tuple[str, str]:
    if "-/" in operation_id:
        method, raw_path = operation_id.split("-", 1)
        return method.upper(), raw_path
    return "GET", operation_id if operation_id.startswith("/") else f"/{operation_id}"


def _path_from_successful_test_case(
    pair: dict[str, Any],
    method: str,
    path_template: str,
    run_dir: Path,
) -> str | None:
    test_cases = _read_json(run_dir / "test_cases.json")
    if not isinstance(test_cases, list):
        return None
    for case in test_cases:
        if not isinstance(case, dict):
            continue
        if not _test_case_matches_pair(case, pair, method, path_template):
            continue
        observed_path = str(case.get("path") or case.get("endpoint_path") or "")
        if observed_path and "{" not in observed_path and "}" not in observed_path:
            return observed_path
        parameters = case.get("parameters")
        if isinstance(parameters, dict):
            substituted = _substitute_path(path_template, parameters)
            if substituted is not None:
                return substituted
    return None


def _test_case_matches_pair(
    case: dict[str, Any],
    pair: dict[str, Any],
    method: str,
    path_template: str,
) -> bool:
    operation_id = str(case.get("operation_id") or "")
    if operation_id and operation_id == pair["operation_id"]:
        return _successful_test_case(case)
    case_method = str(case.get("method") or case.get("http_method") or "").upper()
    case_path = str(case.get("path") or case.get("endpoint_path") or "")
    if case_method and case_method != method:
        return False
    if case_path and _same_template_shape(case_path, path_template):
        return _successful_test_case(case)
    return False


def _successful_test_case(case: dict[str, Any]) -> bool:
    if case.get("success") is True:
        return True
    status = case.get("status_code")
    if isinstance(status, int):
        return 200 <= status < 400
    if isinstance(status, str) and status.isdigit():
        return 200 <= int(status) < 400
    return False


def _same_template_shape(path: str, template: str) -> bool:
    pattern = "^" + re.sub(r"\\{[^/]+\\}", r"[^/]+", re.escape(template)) + "$"
    return bool(re.match(pattern, path))


def _path_from_openapi_defaults(
    pair: dict[str, Any],
    method: str,
    path_template: str,
    run_dir: Path,
) -> str | None:
    spec = _read_json(run_dir / "specification.json") or _read_json(
        run_dir / "baseline_specification.json"
    )
    if not isinstance(spec, dict):
        return None
    parameters = _operation_path_parameters(spec, pair["operation_id"], method, path_template)
    if not parameters:
        return None
    values: dict[str, Any] = {}
    for parameter in parameters:
        name = str(parameter.get("name") or "")
        if not name:
            continue
        value = _example_value_for_parameter(parameter)
        if value is not None:
            values[name] = value
    return _substitute_path(path_template, values)


def _operation_path_parameters(
    spec: dict[str, Any],
    operation_id: str,
    method: str,
    path_template: str,
) -> list[dict[str, Any]]:
    operation = _operation_spec(spec, operation_id, method, path_template)
    parameters: list[dict[str, Any]] = []
    path_item = _path_item(spec, path_template)
    if isinstance(path_item, dict) and isinstance(path_item.get("parameters"), list):
        parameters.extend(
            parameter
            for parameter in path_item["parameters"]
            if isinstance(parameter, dict) and parameter.get("in") == "path"
        )
    if isinstance(operation, dict) and isinstance(operation.get("parameters"), list):
        parameters.extend(
            parameter
            for parameter in operation["parameters"]
            if isinstance(parameter, dict) and parameter.get("in") == "path"
        )
    if isinstance(operation, dict) and not parameters:
        raw_parameters = operation.get("parameters")
        if isinstance(raw_parameters, dict):
            for name, value in raw_parameters.items():
                if isinstance(value, dict) and value.get("in") == "path":
                    parameters.append({"name": name, **value})
    return parameters


def _operation_spec(
    spec: dict[str, Any],
    operation_id: str,
    method: str,
    path_template: str,
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
                str(item.get("operation_id") or item.get("operationId") or "")
                == operation_id
            ):
                return item
    path_item = _path_item(spec, path_template)
    if isinstance(path_item, dict):
        operation = path_item.get(method.lower())
        if isinstance(operation, dict):
            return operation
    return None


def _path_item(spec: dict[str, Any], path_template: str) -> dict[str, Any] | None:
    paths = spec.get("paths")
    if isinstance(paths, dict):
        item = paths.get(path_template)
        if isinstance(item, dict):
            return item
    return None


def _example_value_for_parameter(parameter: dict[str, Any]) -> Any:
    for key in ("example", "default"):
        if key in parameter:
            return parameter[key]
    examples = parameter.get("examples")
    if isinstance(examples, dict):
        for example in examples.values():
            if isinstance(example, dict) and "value" in example:
                return example["value"]
            if example is not None:
                return example
    schema = parameter.get("schema")
    return _example_value_for_schema(schema if isinstance(schema, dict) else {})


def _example_value_for_schema(schema: dict[str, Any]) -> Any:
    for key in ("example", "default", "const"):
        if key in schema:
            return schema[key]
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    schema_type = schema.get("type")
    if schema_type == "integer":
        minimum = schema.get("minimum")
        return minimum if isinstance(minimum, int) else 1
    if schema_type == "number":
        minimum = schema.get("minimum")
        return minimum if isinstance(minimum, (int, float)) else 1
    if schema_type == "boolean":
        return True
    return "sample"


def _substitute_path(path_template: str, values: dict[str, Any]) -> str | None:
    missing = False

    def replace(match: re.Match[str]) -> str:
        nonlocal missing
        name = match.group(1)
        value = values.get(name)
        if value is None or value == "":
            missing = True
            return match.group(0)
        return str(value)

    resolved = re.sub(r"\{([^}/]+)\}", replace, path_template)
    return None if missing or "{" in resolved or "}" in resolved else resolved


def _invalid_reason_for_request(
    request: dict[str, Any],
    config: ResearchAutomationConfig,
) -> str:
    method = str(request.get("method", "GET")).upper()
    if method != "GET" and not (config.allow_non_get and config.confirm_unsafe_methods):
        return "unsafe_method_blocked"
    if not str(request.get("method") or "").strip() or not str(request.get("path") or "").strip():
        return "schema_mismatch"
    if "{" in str(request.get("path", "")):
        return "path_param_unresolved"
    return ""


def _invalid_detail_for_reason(reason: str, request: dict[str, Any]) -> str:
    if reason == "unsafe_method_blocked":
        return f"{str(request.get('method') or 'GET').upper()} requires allow_non_get and confirm_unsafe_methods."
    if reason == "path_param_unresolved":
        return "Request path still contains unresolved template parameters."
    if reason == "schema_mismatch":
        return "Request is missing a method or path."
    if reason == "execution_timeout":
        return "HTTP request timed out before an evaluable response was available."
    if reason == "http_error":
        return "HTTP request failed before an evaluable response was available."
    return ""


def _execution_invalid_reason(execution: dict[str, Any]) -> str:
    runtime_result = execution.get("runtime_result")
    if not isinstance(runtime_result, dict):
        return ""
    reason = runtime_result.get("invalid_reason")
    return str(reason) if reason else ""


def _requests_executor(base_url: str, timeout_seconds: float) -> Executor:
    def execute(request: dict[str, Any]) -> dict[str, Any]:
        method = str(request.get("method") or "GET")
        url = urljoin(
            base_url.rstrip("/") + "/", str(request.get("path", "")).lstrip("/")
        )
        try:
            response = requests.request(
                method,
                url,
                params=request.get("query") or {},
                headers=request.get("headers") or {},
                json=request.get("body") if request.get("body") is not None else None,
                timeout=timeout_seconds,
            )
        except requests.exceptions.Timeout:
            return {
                "runtime_verdict": "INCONCLUSIVE",
                "runtime_result": {"invalid_reason": "execution_timeout"},
            }
        except requests.exceptions.RequestException:
            return {
                "runtime_verdict": "INCONCLUSIVE",
                "runtime_result": {"invalid_reason": "http_error"},
            }
        return {
            "response": ResponseData.from_requests(response),
            "runtime_result": {
                "status_code": response.status_code,
                "headers": dict(response.headers),
            },
        }

    return execute


def _runtime_evidence_from_execution(
    *,
    pair: dict[str, Any],
    request: dict[str, Any],
    execution: dict[str, Any],
    index: int,
    run_dir: Path,
) -> tuple[str, str, dict[str, Any]]:
    if execution.get("runtime_verdict"):
        runtime_verdict = str(execution.get("runtime_verdict") or "INCONCLUSIVE")
        reduction = reduce_runtime_evidence(
            relation=pair["relation"],
            cases=[{"runtime_verdict": runtime_verdict}],
        )
        return (
            runtime_verdict,
            reduction.runtime_recommendation,
            _sanitize_summary(execution.get("runtime_result") or {}),
        )

    response = execution.get("response")
    if isinstance(response, ResponseData):
        try:
            request_data = counter_example_request_to_request_data(request)
            detail = SimpleNamespace(
                operation_id=pair["operation_id"],
                property_path=pair["property_path"],
                static_constraint=pair["static_constraint"],
                dynamic_constraint=pair["dynamic_constraint"],
            )
            evaluated = evaluate_counter_example_runtime_case(
                run_name=run_dir.name,
                detail=detail,
                request=request_data,
                response=response,
                index=index,
                cache_root=run_dir.parent,
            )
            runtime_verdict = str(evaluated.get("runtime_verdict") or "INCONCLUSIVE")
            reduction = reduce_runtime_evidence(
                relation=pair["relation"],
                cases=[{"runtime_verdict": runtime_verdict}],
            )
            return runtime_verdict, reduction.runtime_recommendation, _sanitize_summary(evaluated)
        except Exception as exc:
            return (
                "INCONCLUSIVE",
                "INCONCLUSIVE",
                {
                    "invalid_reason": "evaluation_error",
                    "message": str(exc),
                },
            )

    result = _sanitize_summary(execution.get("runtime_result") or {})
    return "INCONCLUSIVE", "INCONCLUSIVE", result


def _last_recommendation(evidence: list[ResearchCaseEvidence]) -> str:
    for item in reversed(evidence):
        if item.runtime_recommendation:
            return item.runtime_recommendation
    return "INCONCLUSIVE"


def _sanitize_summary(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(
                part in lowered
                for part in (
                    "token",
                    "secret",
                    "password",
                    "authorization",
                    "cookie",
                    "api_key",
                )
            ):
                result[str(key)] = "<REDACTED>"
            else:
                result[str(key)] = _sanitize_summary(item)
        return result
    if isinstance(value, list):
        return [_sanitize_summary(item) for item in value]
    if isinstance(value, str) and value.lower().startswith("bearer "):
        return "<REDACTED>"
    return value


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _combination_id(pair: dict[str, Any]) -> str:
    raw = "\x1f".join(
        [
            pair["operation_id"],
            pair["property_path"],
            pair["status"],
            pair["relation"],
            pair["static_constraint"],
            pair["dynamic_constraint"],
            pair["final_constraint"],
        ]
    )
    return f"cmb_{sha256(raw.encode('utf-8')).hexdigest()[:20]}"


def _timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


if __name__ == "__main__":
    main()
