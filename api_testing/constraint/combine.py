import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from api_testing.config.config_loader import load_config
from api_testing.constraint.combine_report import generate_combination_report
from api_testing.constraint.conflict_resolver import ConstraintConflictResolver
from api_testing.constraint.constraint_combiner import ConstraintCombiner
from api_testing.prompts.factory import PromptFactory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine cached static/dynamic constraints and optionally verify conflicts."
    )
    parser.add_argument("--cache-dir", required=True, help="Directory containing miner JSON files.")
    parser.add_argument(
        "--config",
        default="configurations.toml",
        help="LLM configuration used to classify static/dynamic relation pairs.",
    )
    parser.add_argument(
        "--without-llm",
        action="store_true",
        help="Match properties only; paired rows are marked UNKNOWN without LLM classification.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run staged counter-examples immediately and write final runtime verdicts.",
    )
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help=(
            "Verify conflicts already present in combine_constraint_miners.json without "
            "re-running matching or LLM staging."
        ),
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="API base URL required by --verify; otherwise read from the config.",
    )
    parser.add_argument(
        "--test-cases",
        type=int,
        default=5,
        help="Maximum number of distinct runtime validation cases per conflict (default: 5).",
    )
    return parser.parse_args()


def resolve_cache_dir(raw_cache_dir: str) -> Path:
    cache_dir = Path(raw_cache_dir)
    if cache_dir.exists():
        return cache_dir

    if "\\ " in raw_cache_dir:
        unescaped_cache_dir = Path(raw_cache_dir.replace("\\ ", " "))
        if unescaped_cache_dir.exists():
            return unescaped_cache_dir

    return cache_dir


def require_cache_file(cache_dir: Path, filename: str) -> Path:
    path = cache_dir / filename
    if path.exists():
        return path
    raise FileNotFoundError(
        f"Required miner artifact is missing: {path}. "
        "Run static/dynamic constraint mining first or pass the correct --cache-dir."
    )


def load_constraints(cache_dir: Path) -> tuple[dict, dict]:
    static_data = json.loads(
        require_cache_file(cache_dir, "static_constraint_miner.json").read_text(
            encoding="utf-8"
        )
    )
    dynamic_data = json.loads(
        require_cache_file(cache_dir, "dynamic_constraint_miner.json").read_text(
            encoding="utf-8"
        )
    )
    return static_data["common"], dynamic_data["constraints"]


def resolve_base_url(cache_dir: Path, supplied_base_url: str | None) -> str:
    if supplied_base_url:
        return supplied_base_url
    baseline_path = cache_dir / "baseline_specification.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        servers = baseline.get("servers") or []
        if isinstance(servers, list) and servers and servers[0].get("url"):
            return servers[0]["url"]
    raise ValueError(
        "--verify requires --base-url unless baseline_specification.json in the cache "
        "contains a server URL"
    )


def main() -> None:
    load_dotenv()
    args = parse_args()
    cache_dir = resolve_cache_dir(args.cache_dir)
    json_path = cache_dir / ConstraintCombiner.MAIN_CACHE
    if args.verify_existing:
        result = json.loads(json_path.read_text(encoding="utf-8"))
    else:
        static_constraints, dynamic_constraints = load_constraints(cache_dir)
        config = load_config(args.config)
        prompt_factory = None if args.without_llm else PromptFactory.from_config(config)
        result = ConstraintCombiner(
            cache_dir=cache_dir,
            prompt_factory=prompt_factory,
            max_test_cases=args.test_cases,
        ).combine(static_constraints, dynamic_constraints)

    if args.verify or args.verify_existing:
        result = ConstraintConflictResolver(
            cache_dir=cache_dir,
            base_url=resolve_base_url(cache_dir, args.base_url),
            max_test_cases=args.test_cases,
        ).resolve(result)

    records = [record for properties in result.values() for record in properties.values()]
    counts: dict[str, int] = {}
    for record in records:
        key = record.get("runtime_verdict") or record["status"]
        counts[key] = counts.get(key, 0) + 1
    report_path = generate_combination_report(json_path)
    print(f"Wrote {json_path}")
    print(f"Wrote {report_path}")
    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
