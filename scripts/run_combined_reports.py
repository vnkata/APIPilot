"""Build and validate combined constraint reports for selected API datasets."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


@dataclass(frozen=True)
class Target:
    name: str
    spec_path: Path
    config_path: Path
    cache_dir: Path
    base_url: str


TARGETS = {
    "canada_holidays": Target(
        name="canada_holidays",
        spec_path=ROOT / "datasets" / "Canada Holidays.json",
        config_path=ROOT / "configurations.canada_holidays.toml",
        cache_dir=ROOT / ".cache" / "CanadaHolidays",
        base_url="https://canada-holidays.ca",
    ),
    "ohsome_20_endpoints": Target(
        name="ohsome_20_endpoints",
        spec_path=ROOT / "datasets" / "ohsome_20_endpoint.json",
        config_path=ROOT / "configurations.ohsome_20_endpoints.toml",
        cache_dir=ROOT / ".cache" / "ohsome",
        base_url="https://api.ohsome.org/v1",
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def operation_signatures(document: dict[str, Any]) -> set[str]:
    paths = document.get("paths") or {}
    return {
        f"{method.lower()}-{path}"
        for path, definition in paths.items()
        for method in definition
        if method.lower() in HTTP_METHODS
    }


def canonical_property(name: str) -> str:
    return re.sub(r"\[\]", "", name or "").strip()


def run_command(arguments: list[str]) -> None:
    display = subprocess.list2cmdline(arguments)
    print(f"\nRunning: {display}", flush=True)
    subprocess.run(arguments, cwd=ROOT, check=True)


def assert_cache_matches_dataset(target: Target) -> None:
    baseline = target.cache_dir / "baseline_specification.json"
    if not baseline.exists():
        return
    requested = operation_signatures(load_json(target.spec_path))
    cached = operation_signatures(load_json(baseline))
    if cached != requested:
        missing = sorted(requested - cached)
        extra = sorted(cached - requested)
        raise RuntimeError(
            f"{target.name}: cache at {target.cache_dir} does not match {target.spec_path}. "
            f"Missing operations: {missing}; unexpected operations: {extra}."
        )


def mining_inputs_ready(target: Target) -> bool:
    return all(
        (target.cache_dir / filename).exists()
        for filename in ("static_constraint_miner.json", "dynamic_constraint_miner.json")
    )


def ensure_mining_inputs(target: Target, force_mine: bool) -> None:
    assert_cache_matches_dataset(target)
    if force_mine or not mining_inputs_ready(target):
        reason = "forced refresh" if force_mine else "missing static/dynamic mining inputs"
        print(f"\n{target.name}: running API testing because of {reason}.", flush=True)
        run_command(
            [
                sys.executable,
                "-m",
                "api_testing",
                "--config",
                str(target.config_path),
                "--skip-wizard",
            ]
        )
        assert_cache_matches_dataset(target)
    if not mining_inputs_ready(target):
        raise RuntimeError(
            f"{target.name}: API testing finished without static and dynamic mining JSON files."
        )


def combine_target(target: Target, without_llm: bool, skip_verify: bool) -> None:
    command = [
        sys.executable,
        "-m",
        "api_testing.constraint.combine",
        "--cache-dir",
        str(target.cache_dir),
        "--config",
        str(target.config_path),
        "--base-url",
        target.base_url,
        "--test-cases",
        "5",
    ]
    if without_llm:
        command.append("--without-llm")
    if not skip_verify:
        command.append("--verify")
    run_command(command)


def expected_record_count(static_data: dict[str, Any], dynamic_data: dict[str, Any]) -> int:
    count = 0
    static_constraints = static_data["common"]
    dynamic_constraints = dynamic_data["constraints"]
    for endpoint in set(static_constraints) | set(dynamic_constraints):
        properties = {
            canonical_property(name)
            for name in set(static_constraints.get(endpoint, {}))
            | set(dynamic_constraints.get(endpoint, {}))
        }
        count += len(properties)
    return count


def validate_report(target: Target) -> dict[str, Any]:
    static_data = load_json(target.cache_dir / "static_constraint_miner.json")
    dynamic_data = load_json(target.cache_dir / "dynamic_constraint_miner.json")
    json_path = target.cache_dir / "combine_constraint_miners.json"
    html_path = target.cache_dir / "combine_constraint_miners.html"
    if not json_path.exists() or json_path.stat().st_size == 0:
        raise RuntimeError(f"{target.name}: combined JSON output is missing or empty: {json_path}")
    if not html_path.exists() or html_path.stat().st_size < 1024:
        raise RuntimeError(f"{target.name}: combined HTML output is missing or too small: {html_path}")

    combined = load_json(json_path)
    expected_endpoints = set(static_data["common"]) | set(dynamic_data["constraints"])
    if set(combined) != expected_endpoints:
        raise RuntimeError(
            f"{target.name}: combined JSON endpoints differ from its mining inputs."
        )

    records = [
        record
        for properties in combined.values()
        for record in properties.values()
        if isinstance(record, dict)
    ]
    required_records = expected_record_count(static_data, dynamic_data)
    if len(records) != required_records or not records:
        raise RuntimeError(
            f"{target.name}: combined JSON contains {len(records)} records; "
            f"expected {required_records} from the mining inputs."
        )

    html = html_path.read_text(encoding="utf-8")
    if "Combined Constraint Report" not in html or "const data =" not in html:
        raise RuntimeError(f"{target.name}: HTML report does not contain the report payload.")

    statuses = Counter(str(record.get("status") or "UNKNOWN") for record in records)
    verdicts = Counter(str(record.get("verdict")) for record in records if record.get("verdict"))
    result = {
        "target": target.name,
        "json": str(json_path.relative_to(ROOT)),
        "html": str(html_path.relative_to(ROOT)),
        "json_bytes": json_path.stat().st_size,
        "html_bytes": html_path.stat().st_size,
        "endpoints": len(combined),
        "records": len(records),
        "statuses": dict(statuses),
        "verdicts": dict(verdicts),
    }
    print("\nValidated report:")
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and validate combined JSON/HTML constraint reports."
    )
    parser.add_argument(
        "--target",
        choices=["all", *TARGETS],
        default="all",
        help="Dataset report to generate (default: all).",
    )
    parser.add_argument(
        "--force-mine",
        action="store_true",
        help="Re-run full API testing even when matching static/dynamic mining files exist.",
    )
    parser.add_argument(
        "--without-llm",
        action="store_true",
        help="Skip LLM counter-example staging while combining.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Do not make runtime verification requests for differing constraints.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    names = list(TARGETS) if args.target == "all" else [args.target]
    results = []
    for name in names:
        target = TARGETS[name]
        ensure_mining_inputs(target, args.force_mine)
        combine_target(target, args.without_llm, args.skip_verify)
        results.append(validate_report(target))
    print(f"\nCompleted {len(results)} combined report(s).")


if __name__ == "__main__":
    main()
