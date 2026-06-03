from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from dotenv import load_dotenv

from api_testing.config.config_loader import load_config
from api_testing.constraint.counter_examples import (
    CounterExampleLLMPlanner,
    build_counter_example_context,
    generate_draft_cases,
)
from api_testing.constraint.counter_examples.planner import PROMPT_VERSION
from api_testing.prompts.factory import PromptFactory

DEFAULT_OUTPUT_ROOT = Path(".cache/_experiments/counter_examples")
TARGET_VECTOR = dict[str, str]


@dataclass(frozen=True)
class CounterExampleExperimentCase:
    case_id: str
    endpoint: str
    property: str
    static_constraint: str | None
    dynamic_constraint: str | None
    relation: str | None
    status: str | None
    expected_target_truth_vector: TARGET_VECTOR | None = None
    source: str = "gold"
    record: dict[str, Any] | None = None


GOLD_CASES: tuple[CounterExampleExperimentCase, ...] = (
    CounterExampleExperimentCase(
        case_id="gold-dynamic-stronger-existence-vs-enum-static-only",
        endpoint="get-/api/v1/Bills",
        property="return.items[].isAct",
        static_constraint="exists(return.items[].isAct)",
        dynamic_constraint="return.items.isAct one of { 0, 1 }",
        relation="DYNAMIC_STRONGER",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-dynamic-stronger-length-vs-nonempty-static-only",
        endpoint="get-/api/v1/Bills/{billId}",
        property="return.sponsors[].member.partyColour",
        static_constraint="gt(size_of(return.sponsors[].member.partyColour), 0)",
        dynamic_constraint="LENGTH(return.sponsors.member.partyColour)==6",
        relation="DYNAMIC_STRONGER",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-dynamic-stronger-total-results-bound-static-only",
        endpoint="get-/api/v1/PublicationTypes",
        property="return.totalResults",
        static_constraint="gte(return.totalResults, 0)",
        dynamic_constraint="return.totalResults >= size(return.items[])",
        relation="DYNAMIC_STRONGER",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-dynamic-stronger-items-per-page-bound-static-only",
        endpoint="get-/api/v1/Stages",
        property="return.itemsPerPage",
        static_constraint="gte(return.itemsPerPage, 0)",
        dynamic_constraint="return.itemsPerPage >= size(return.items[])",
        relation="DYNAMIC_STRONGER",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-static-stronger-federal-filter-dynamic-only",
        endpoint="get-/api/v1/holidays",
        property="return.holidays[].federal",
        static_constraint=(
            "and(in(return.holidays[].federal, [0, 1]), "
            "implies(exists(input.federal), eq(return.holidays[].federal, input.federal)))"
        ),
        dynamic_constraint="return.holidays.federal one of { 0, 1 }",
        relation="STATIC_STRONGER",
        status="RESOLVED",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-static-stronger-province-code-dynamic-only",
        endpoint="get-/api/v1/provinces",
        property="return.provinces[].id",
        static_constraint="in(return.provinces[].id, ['AB', 'BC', 'ON', 'QC'])",
        dynamic_constraint="LENGTH(return.provinces.id)==2",
        relation="STATIC_STRONGER",
        status="RESOLVED",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-static-stronger-holiday-id-range-dynamic-only",
        endpoint="get-/api/v1/holidays",
        property="return.holidays[].id",
        static_constraint="and(gte(return.holidays[].id, 1), lte(return.holidays[].id, 34))",
        dynamic_constraint="return.holidays.id >= 1",
        relation="STATIC_STRONGER",
        status="RESOLVED",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-static-stronger-nested-province-code-dynamic-only",
        endpoint="get-/api/v1/holidays",
        property="return.holidays[].provinces[].id",
        static_constraint="in(return.holidays[].provinces[].id, ['AB', 'BC', 'ON', 'QC'])",
        dynamic_constraint="LENGTH(return.holidays.provinces.id)==2",
        relation="STATIC_STRONGER",
        status="RESOLVED",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-partial-overlap-datetime-vs-length-static-only",
        endpoint="get-/api/v1/Bills/{billId}",
        property="return.lastUpdate",
        static_constraint="isDateTime(return.lastUpdate)",
        dynamic_constraint="LENGTH(return.lastUpdate)==19",
        relation="PARTIAL_OVERLAP",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-partial-overlap-datetime-vs-length-dynamic-only",
        endpoint="get-/api/v1/Bills/{billId}",
        property="return.lastUpdate",
        static_constraint="isDateTime(return.lastUpdate)",
        dynamic_constraint="LENGTH(return.lastUpdate)==19",
        relation="PARTIAL_OVERLAP",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-partial-overlap-category-filter-static-only",
        endpoint="get-/api/v1/BillTypes",
        property="return.items[].category",
        static_constraint="implies(exists(input.Category), eq(return.items[].category, input.Category))",
        dynamic_constraint='return.items.category one of { "Hybrid", "Private", "Public" }',
        relation="PARTIAL_OVERLAP",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-partial-overlap-category-filter-dynamic-only",
        endpoint="get-/api/v1/BillTypes",
        property="return.items[].category",
        static_constraint="implies(exists(input.Category), eq(return.items[].category, input.Category))",
        dynamic_constraint='return.items.category one of { "Hybrid", "Private", "Public" }',
        relation="PARTIAL_OVERLAP",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-partial-overlap-holiday-year-static-only",
        endpoint="get-/api/v1/holidays/{holidayId}",
        property="return.holiday.date",
        static_constraint="and(isDate(return.holiday.date), implies(exists(input.year), eq(year(return.holiday.date), input.year)))",
        dynamic_constraint="return.holiday.date is a Date. Format: YYYY/MM/DD",
        relation="PARTIAL_OVERLAP",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-partial-overlap-holiday-year-dynamic-only",
        endpoint="get-/api/v1/holidays/{holidayId}",
        property="return.holiday.date",
        static_constraint="and(isDate(return.holiday.date), implies(exists(input.year), eq(year(return.holiday.date), input.year)))",
        dynamic_constraint="return.holiday.date is a Date. Format: YYYY/MM/DD",
        relation="PARTIAL_OVERLAP",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
    ),
    CounterExampleExperimentCase(
        case_id="gold-disjoint-status-static-side",
        endpoint="get-/synthetic",
        property="return.status",
        static_constraint='eq(return.status, "active")',
        dynamic_constraint='return.status == "archived"',
        relation="DISJOINT",
        status="CONFLICT",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
        source="synthetic",
    ),
    CounterExampleExperimentCase(
        case_id="gold-disjoint-status-dynamic-side",
        endpoint="get-/synthetic",
        property="return.status",
        static_constraint='eq(return.status, "active")',
        dynamic_constraint='return.status == "archived"',
        relation="DISJOINT",
        status="CONFLICT",
        expected_target_truth_vector={
            "static_constraint": "false",
            "dynamic_constraint": "true",
        },
        source="synthetic",
    ),
    CounterExampleExperimentCase(
        case_id="gold-disjoint-range-static-side",
        endpoint="get-/synthetic",
        property="return.age",
        static_constraint="and(gte(return.age, 0), lte(return.age, 10))",
        dynamic_constraint="return.age >= 100",
        relation="DISJOINT",
        status="CONFLICT",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
        source="synthetic",
    ),
    CounterExampleExperimentCase(
        case_id="gold-unknown-business-policy-diagnostic",
        endpoint="get-/synthetic",
        property="return.score",
        static_constraint="return.score follows the documented business policy",
        dynamic_constraint="return.score usually increases after approval",
        relation="UNKNOWN",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "unknown",
            "dynamic_constraint": "unknown",
        },
        source="synthetic",
    ),
    CounterExampleExperimentCase(
        case_id="gold-unknown-natural-language-policy-diagnostic",
        endpoint="get-/synthetic",
        property="return.category",
        static_constraint="return.category is suitable for the user segment",
        dynamic_constraint="return.category matches historical behavior",
        relation="UNKNOWN",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "unknown",
            "dynamic_constraint": "unknown",
        },
        source="synthetic",
    ),
    CounterExampleExperimentCase(
        case_id="gold-dynamic-stronger-membership-static-only",
        endpoint="get-/api/v1/Bills",
        property="return.items[].introducedSessionId",
        static_constraint="gt(return.items[].introducedSessionId, 0)",
        dynamic_constraint="return.items.introducedSessionId in return.items.includedSessionIds[]",
        relation="DYNAMIC_STRONGER",
        status="UNRESOLVED",
        expected_target_truth_vector={
            "static_constraint": "true",
            "dynamic_constraint": "false",
        },
    ),
)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def build_counter_example_cases_from_combine(
    data: Mapping[str, Any],
    *,
    source: str,
) -> list[CounterExampleExperimentCase]:
    cases: list[CounterExampleExperimentCase] = []
    for endpoint, properties in data.items():
        if not isinstance(properties, Mapping):
            continue
        for property_path, record in properties.items():
            if not isinstance(record, Mapping):
                continue
            static_constraint = record.get("static_constraint")
            dynamic_constraint = record.get("dynamic_constraint")
            if not static_constraint or not dynamic_constraint:
                continue
            relation = record.get("relation")
            if relation is None:
                continue
            cases.append(
                CounterExampleExperimentCase(
                    case_id=f"{source}:{len(cases) + 1}",
                    endpoint=str(record.get("endpoint") or endpoint),
                    property=str(record.get("property") or property_path),
                    static_constraint=str(static_constraint),
                    dynamic_constraint=str(dynamic_constraint),
                    relation=str(relation),
                    status=(
                        str(record["status"])
                        if record.get("status") is not None
                        else None
                    ),
                    expected_target_truth_vector=None,
                    source=source,
                    record=dict(record),
                )
            )
    return cases


def load_counter_example_cases_from_cache(
    cache_dir: str | Path,
) -> list[CounterExampleExperimentCase]:
    cache_path = Path(cache_dir)
    data = _load_json(cache_path / "combine_constraint_miners.json", {})
    return build_counter_example_cases_from_combine(data, source=cache_path.name)


def _load_context_artifacts(cache_dir: str | Path | None) -> dict[str, Any]:
    if cache_dir is None:
        return {}
    cache_path = Path(cache_dir)
    return {
        "openapi_spec": _load_json(cache_path / "specification.json", None),
        "reports": _load_json(cache_path / "reports.json", []),
        "test_cases": _load_json(cache_path / "test_cases.json", []),
        "contextual_memory": _load_json(cache_path / "contextual_memory.json", {}),
    }


def _case_mapping(case: CounterExampleExperimentCase) -> dict[str, Any]:
    payload = case.record.copy() if case.record else {}
    payload.update(
        {
            "case_id": case.case_id,
            "endpoint": case.endpoint,
            "operation_id": case.endpoint,
            "property": case.property,
            "property_path": case.property,
            "static_constraint": case.static_constraint,
            "dynamic_constraint": case.dynamic_constraint,
            "relation": case.relation,
            "status": case.status,
            "expected_target_truth_vector": case.expected_target_truth_vector,
        }
    )
    return payload


def _matches_expected_vector(
    draft: dict[str, Any] | None,
    expected: TARGET_VECTOR | None,
) -> bool | None:
    if expected is None:
        return None
    if not draft:
        return False
    return draft.get("target_truth_vector") == expected


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _write_mismatch_report(path: Path, mismatches: Sequence[Mapping[str, Any]]) -> None:
    lines = ["# Counter-Example Planner Mismatch Report", ""]
    if not mismatches:
        lines.append("No labeled gold mismatches.")
    for item in mismatches:
        lines.extend(
            [
                f"## {item['case_id']}",
                "",
                f"- Expected target: `{item.get('expected_target_truth_vector')}`",
                f"- Actual target: `{item.get('actual_target_truth_vector')}`",
                f"- Error: `{item.get('planner_error')}`",
                "",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_counter_example_cases(
    cases: Sequence[CounterExampleExperimentCase],
    planner: Any,
    output_dir: str | Path,
    *,
    context_artifacts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    artifacts = context_artifacts or {}

    case_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    for case in cases:
        context = build_counter_example_context(
            _case_mapping(case),
            openapi_spec=artifacts.get("openapi_spec"),
            reports=artifacts.get("reports"),
            test_cases=artifacts.get("test_cases"),
            contextual_memory=artifacts.get("contextual_memory"),
        )
        draft_cases = generate_draft_cases(context, planner)
        draft_payloads = [asdict(item) for item in draft_cases]
        actual_first = draft_payloads[0] if draft_payloads else None
        matched = _matches_expected_vector(
            actual_first,
            case.expected_target_truth_vector,
        )
        planner_error = getattr(planner, "last_error", None)
        for interaction in getattr(planner, "last_interactions", []) or []:
            raw_rows.append(
                {
                    "case_id": case.case_id,
                    "source": case.source,
                    **dict(interaction),
                }
            )
        case_rows.append(
            {
                **asdict(case),
                "draft_cases": draft_payloads,
                "actual_target_truth_vector": (
                    actual_first.get("target_truth_vector") if actual_first else None
                ),
                "matched": matched,
                "planner_error": planner_error,
            }
        )

    labeled = [
        item for item in case_rows if item["expected_target_truth_vector"] is not None
    ]
    matches = [item for item in labeled if item["matched"]]
    mismatches = [item for item in labeled if not item["matched"]]
    summary = {
        "prompt_version": PROMPT_VERSION,
        "total_cases": len(case_rows),
        "gold_cases": len(labeled),
        "gold_matches": len(matches),
        "gold_accuracy": len(matches) / len(labeled) if labeled else None,
        "mismatch_count": len(mismatches),
    }
    _write_jsonl(output_path / "cases.jsonl", case_rows)
    _write_jsonl(output_path / "raw_prompts_responses.jsonl", raw_rows)
    (output_path / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_mismatch_report(output_path / "mismatch_report.md", mismatches)
    return summary


def run_counter_example_experiment(
    *,
    planner: Any | None = None,
    model: Any | None = None,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
    gold_cases: Sequence[CounterExampleExperimentCase] = GOLD_CASES,
    cache_dirs: Sequence[str | Path] = (),
    include_full: bool = False,
    allow_non_get: bool = False,
    confirm_unsafe_methods: bool = False,
) -> Path:
    if planner is None:
        if model is None:
            raise ValueError("model or planner is required")
        planner = CounterExampleLLMPlanner(llm=model)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    experiment_id = run_id or timestamp
    run_dir = Path(output_root) / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    all_cases = list(gold_cases)
    context_artifacts: dict[str, Any] = {}
    if include_full:
        for cache_dir in cache_dirs:
            loaded_cases = load_counter_example_cases_from_cache(cache_dir)
            all_cases.extend(loaded_cases)
            if not context_artifacts:
                context_artifacts = _load_context_artifacts(cache_dir)

    metadata = {
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "cache_dirs": [str(Path(path)) for path in cache_dirs],
        "include_full": include_full,
        "allow_non_get": allow_non_get,
        "confirm_unsafe_methods": confirm_unsafe_methods,
        "live_execution": False,
        "live_execution_note": (
            "This core-only batch generates draft cases only; approved live "
            "execution remains a follow-up/backend HITL concern."
        ),
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    evaluate_counter_example_cases(
        all_cases,
        planner,
        run_dir,
        context_artifacts=context_artifacts,
    )
    return run_dir


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the counter-example draft planner prompt."
    )
    parser.add_argument(
        "--config",
        default="configurations.toml",
        help="LLM configuration used for counter-example planning.",
    )
    parser.add_argument(
        "--cache-dir",
        action="append",
        default=[],
        help="Cache directory to include when --full-paired is set.",
    )
    parser.add_argument(
        "--gold-only",
        action="store_true",
        help="Evaluate curated gold cases only.",
    )
    parser.add_argument(
        "--full-paired",
        action="store_true",
        help="Also evaluate paired records from combine_constraint_miners.json.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory root for local experiment outputs.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional deterministic experiment directory name.",
    )
    parser.add_argument(
        "--allow-non-get",
        action="store_true",
        help="Record that non-GET draft planning is allowed for this manual run.",
    )
    parser.add_argument(
        "--confirm-unsafe-methods",
        action="store_true",
        help="Record explicit unsafe-method confirmation for this manual run.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    load_dotenv()
    args = parse_args(argv)
    config = load_config(args.config)
    planner = PromptFactory.from_config(config).create(CounterExampleLLMPlanner)
    include_full = bool(args.full_paired and not args.gold_only)
    run_dir = run_counter_example_experiment(
        planner=planner,
        output_root=args.output_root,
        run_id=args.run_id,
        cache_dirs=args.cache_dir,
        include_full=include_full,
        allow_non_get=args.allow_non_get,
        confirm_unsafe_methods=args.confirm_unsafe_methods,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
