from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from dotenv import load_dotenv

from api_testing.config.config_loader import load_config
from api_testing.constraint.constraint_combiner import ConstraintCombiner
from api_testing.prompts.constraint_combination import ConstraintCombination
from api_testing.prompts.factory import PromptFactory

PROMPT_VERSION = "constraint-relation-classifier-v12"
DEFAULT_OUTPUT_ROOT = Path(".cache/_experiments/constraint_relation")


@dataclass(frozen=True)
class RelationCase:
    case_id: str
    endpoint: str
    property: str
    static_constraint: str
    dynamic_constraint: str
    expected_relation: str | None = None
    source: str = "gold"


GOLD_CASES: tuple[RelationCase, ...] = (
    RelationCase(
        case_id="gold-equivalent-positive-integer-id",
        endpoint="get-/api/v1/BillTypes",
        property="return.items[].id",
        static_constraint="gt(return.items[].id, 0)",
        dynamic_constraint="return.items.id >= 1",
        expected_relation="EQUIVALENT",
    ),
    RelationCase(
        case_id="gold-dynamic-stronger-existence-vs-enum",
        endpoint="get-/api/v1/Bills",
        property="return.items[].isAct",
        static_constraint="exists(return.items[].isAct)",
        dynamic_constraint="return.items.isAct one of { 0, 1 }",
        expected_relation="DYNAMIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-dynamic-stronger-exact-length-vs-nonempty",
        endpoint="get-/api/v1/Bills/{billId}",
        property="return.sponsors[].member.partyColour",
        static_constraint="gt(size_of(return.sponsors[].member.partyColour), 0)",
        dynamic_constraint="LENGTH(return.sponsors.member.partyColour)==6",
        expected_relation="DYNAMIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-partial-overlap-datetime-vs-raw-length",
        endpoint="get-/api/v1/Bills/{billId}",
        property="return.lastUpdate",
        static_constraint="isDateTime(return.lastUpdate)",
        dynamic_constraint="LENGTH(return.lastUpdate)==19",
        expected_relation="PARTIAL_OVERLAP",
    ),
    RelationCase(
        case_id="gold-partial-overlap-input-or-membership-vs-membership",
        endpoint="get-/api/v1/Bills",
        property="return.items[].introducedSessionId",
        static_constraint=(
            "and(gt(return.items[].introducedSessionId, 0),"
            "implies(exists(input.Session), "
            "or(eq(return.items[].introducedSessionId, input.Session), "
            "contains(return.items.includedSessionIds, input.Session))))"
        ),
        dynamic_constraint=(
            "return.items.introducedSessionId in return.items.includedSessionIds[]"
        ),
        expected_relation="PARTIAL_OVERLAP",
    ),
    RelationCase(
        case_id="gold-partial-overlap-date-year-guard-vs-format-only",
        endpoint="get-/api/v1/holidays/{holidayId}",
        property="return.holiday.date",
        static_constraint=(
            "and(isDate(return.holiday.date),"
            "implies(exists(input.year), eq(year(return.holiday.date), input.year)))"
        ),
        dynamic_constraint="return.holiday.date is a Date. Format: YYYY/MM/DD",
        expected_relation="PARTIAL_OVERLAP",
    ),
    RelationCase(
        case_id="gold-equivalent-url-plus-redundant-nonempty",
        endpoint="get-/api/v1/Bills/{billId}/Publications",
        property="return.publications[].links[].url",
        static_constraint=(
            "and(isURL(return.publications[].links[].url), "
            "gt(size_of(return.publications[].links[].url), 0))"
        ),
        dynamic_constraint="return.publications.links.url is Url",
        expected_relation="EQUIVALENT",
    ),
    RelationCase(
        case_id="gold-dynamic-stronger-size-bound-vs-nonnegative",
        endpoint="get-/api/v1/PublicationTypes",
        property="return.totalResults",
        static_constraint="gte(return.totalResults, 0)",
        dynamic_constraint="return.totalResults >= size(return.items[])",
        expected_relation="DYNAMIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-dynamic-stronger-item-count-bound-vs-nonnegative",
        endpoint="get-/api/v1/Stages",
        property="return.itemsPerPage",
        static_constraint="gte(return.itemsPerPage, 0)",
        dynamic_constraint="return.itemsPerPage >= size(return.items[])",
        expected_relation="DYNAMIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-static-stronger-input-match-plus-enum",
        endpoint="get-/api/v1/holidays",
        property="return.holidays[].federal",
        static_constraint=(
            "and(in(return.holidays[].federal, [0, 1]),"
            "implies(exists(input.federal), "
            "eq(return.holidays[].federal, or(eq(input.federal, '1'), "
            "eq(input.federal, 'true')))))"
        ),
        dynamic_constraint="return.holidays.federal one of { 0, 1 }",
        expected_relation="STATIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-static-stronger-code-enum-vs-length",
        endpoint="get-/api/v1/provinces",
        property="return.provinces[].id",
        static_constraint=(
            "in(return.provinces[].id, ['AB', 'BC', 'MB', 'NB', 'NL', 'NS', "
            "'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'])"
        ),
        dynamic_constraint="LENGTH(return.provinces.id)==2",
        expected_relation="STATIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-static-stronger-nested-code-enum-vs-length",
        endpoint="get-/api/v1/holidays",
        property="return.holidays[].provinces[].id",
        static_constraint=(
            "in(return.holidays[].provinces[].id, ['AB', 'BC', 'MB', 'NB', "
            "'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT'])"
        ),
        dynamic_constraint="LENGTH(return.holidays.provinces.id)==2",
        expected_relation="STATIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-static-stronger-bounded-range-vs-lower-bound",
        endpoint="get-/api/v1/holidays",
        property="return.holidays[].id",
        static_constraint="and(gte(return.holidays[].id, 1), lte(return.holidays[].id, 34))",
        dynamic_constraint="return.holidays.id >= 1",
        expected_relation="STATIC_STRONGER",
    ),
    RelationCase(
        case_id="gold-partial-overlap-input-filter-vs-observed-enum",
        endpoint="get-/api/v1/BillTypes",
        property="return.items[].category",
        static_constraint=(
            "implies(exists(input.Category), "
            "eq(return.items[].category, input.Category))"
        ),
        dynamic_constraint='return.items.category one of { "Hybrid", "Private", "Public" }',
        expected_relation="PARTIAL_OVERLAP",
    ),
    RelationCase(
        case_id="gold-disjoint-conflicting-literals",
        endpoint="get-/synthetic",
        property="return.status",
        static_constraint='eq(return.status, "active")',
        dynamic_constraint='return.status == "archived"',
        expected_relation="DISJOINT",
        source="synthetic",
    ),
    RelationCase(
        case_id="gold-unknown-business-policy",
        endpoint="get-/synthetic",
        property="return.score",
        static_constraint="return.score follows the documented business policy",
        dynamic_constraint="return.score usually increases after approval",
        expected_relation="UNKNOWN",
        source="synthetic",
    ),
)


def build_relation_cases(
    static_constraints: Mapping[str, Mapping[str, str]],
    dynamic_constraints: Mapping[str, Mapping[str, str]],
    *,
    source: str,
) -> list[RelationCase]:
    cases: list[RelationCase] = []
    for endpoint in sorted(set(static_constraints) | set(dynamic_constraints)):
        static_index = ConstraintCombiner._index_constraints(
            dict(static_constraints.get(endpoint, {}))
        )
        dynamic_index = ConstraintCombiner._index_constraints(
            dict(dynamic_constraints.get(endpoint, {}))
        )
        for canonical in sorted(set(static_index) & set(dynamic_index)):
            static_item = static_index[canonical]
            dynamic_item = dynamic_index[canonical]
            cases.append(
                RelationCase(
                    case_id=f"{source}:{len(cases) + 1}",
                    endpoint=endpoint,
                    property=static_item["property"],
                    static_constraint=static_item["constraint"],
                    dynamic_constraint=dynamic_item["constraint"],
                    expected_relation=None,
                    source=source,
                )
            )
    return cases


def load_relation_cases_from_cache(cache_dir: str | Path) -> list[RelationCase]:
    cache_path = Path(cache_dir)
    static_data = json.loads(
        (cache_path / "static_constraint_miner.json").read_text(encoding="utf-8")
    )
    dynamic_data = json.loads(
        (cache_path / "dynamic_constraint_miner.json").read_text(encoding="utf-8")
    )
    return build_relation_cases(
        static_constraints=static_data["common"],
        dynamic_constraints=dynamic_data["constraints"],
        source=cache_path.name,
    )


def _case_prompt(case: RelationCase) -> str:
    return ConstraintCombination.PROMPT.format(
        endpoint=case.endpoint,
        property=case.property,
        static_constraint=case.static_constraint,
        dynamic_constraint=case.dynamic_constraint,
    )


def evaluate_relation_cases(
    cases: Sequence[RelationCase],
    combination_prompt: ConstraintCombination,
    output_dir: str | Path,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    raw_prompt_path = output_path / "raw_prompts.jsonl"
    raw_response_path = output_path / "raw_responses.jsonl"
    with raw_prompt_path.open("w", encoding="utf-8") as prompt_file, raw_response_path.open(
        "w", encoding="utf-8"
    ) as response_file:
        for case in cases:
            prompt_text = _case_prompt(case)
            prompt_file.write(
                json.dumps(
                    {
                        "case_id": case.case_id,
                        "system_prompt": ConstraintCombination.SYSTEM_PROMPT,
                        "prompt": prompt_text,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            try:
                verdict = combination_prompt.exec(**asdict(case), test_case_count=1)
                response_payload: dict[str, Any] = verdict.model_dump()
                relation = verdict.relation
                reason = verdict.reason
                error = None
            except Exception as exc:
                response_payload = {"relation": "UNKNOWN", "reason": str(exc)}
                relation = "UNKNOWN"
                reason = "Relation classification failed."
                error = str(exc)

            response_file.write(
                json.dumps(
                    {
                        "case_id": case.case_id,
                        "response": response_payload,
                        "error": error,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            results.append(
                {
                    **asdict(case),
                    "actual_relation": relation,
                    "actual_reason": reason,
                    "matched": (
                        relation == case.expected_relation
                        if case.expected_relation is not None
                        else None
                    ),
                    "error": error,
                }
            )

    labeled = [item for item in results if item["expected_relation"] is not None]
    matches = [item for item in labeled if item["matched"]]
    mismatches = [item for item in labeled if not item["matched"]]
    accuracy = len(matches) / len(labeled) if labeled else None
    summary = {
        "prompt_version": PROMPT_VERSION,
        "total_cases": len(results),
        "labeled_cases": len(labeled),
        "matched_cases": len(matches),
        "accuracy": accuracy,
        "mismatches": mismatches,
    }
    (output_path / "cases.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_path / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def run_relation_experiment(
    *,
    model: Any | None = None,
    combination_prompt: ConstraintCombination | None = None,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
    gold_cases: Sequence[RelationCase] = GOLD_CASES,
    cache_dirs: Sequence[str | Path] = (),
    include_full: bool = False,
) -> Path:
    if combination_prompt is None:
        if model is None:
            raise ValueError("model or combination_prompt is required")
        combination_prompt = ConstraintCombination(llm=model)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    experiment_id = run_id or timestamp
    run_dir = Path(output_root) / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "cache_dirs": [str(Path(path)) for path in cache_dirs],
        "include_full": include_full,
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    evaluate_relation_cases(gold_cases, combination_prompt, run_dir / "gold")

    if include_full:
        full_cases: list[RelationCase] = []
        for cache_dir in cache_dirs:
            full_cases.extend(load_relation_cases_from_cache(cache_dir))
        evaluate_relation_cases(full_cases, combination_prompt, run_dir / "full")

    return run_dir


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the constraint relation classifier prompt."
    )
    parser.add_argument(
        "--config",
        default="configurations.toml",
        help="LLM configuration used for relation classification.",
    )
    parser.add_argument(
        "--cache-dir",
        action="append",
        default=[],
        help="Cache directory to include when --full-paired is set.",
    )
    parser.add_argument(
        "--full-paired",
        action="store_true",
        help="Also evaluate all paired static/dynamic constraints from --cache-dir.",
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    load_dotenv()
    args = parse_args(argv)
    config = load_config(args.config)
    prompt = PromptFactory.from_config(config).create(ConstraintCombination)
    run_dir = run_relation_experiment(
        combination_prompt=prompt,
        output_root=args.output_root,
        run_id=args.run_id,
        cache_dirs=args.cache_dir,
        include_full=args.full_paired,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
