import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


EndpointMap = Dict[str, Tuple[str, str]]
EvidenceMap = Dict[str, Tuple[str, str]]
SUPPORTED_METHODS = {"get", "post", "put", "delete", "head", "options", "patch"}


def _endpoint_key(method: str, path_template: str) -> str:
    return f"{method.lower()}-{path_template.strip()}"


def _normalize_entry_endpoint(entry: dict) -> Optional[str]:
    request = entry.get("request", {})
    method = request.get("method")
    path_template = request.get("path_template")
    if not method or not path_template:
        return None
    return _endpoint_key(method, path_template)


def _load_endpoints_from_cached_spec(raw: dict) -> EndpointMap:
    endpoints: EndpointMap = {}
    for op in raw["operations"].values():
        method = op.get("http_method")
        path_template = op.get("endpoint_path")
        if not method or not path_template:
            continue
        key = _endpoint_key(method, path_template)
        endpoints[key] = (method.lower(), path_template)
    return endpoints


def _load_endpoints_from_openapi(raw: dict) -> EndpointMap:
    endpoints: EndpointMap = {}
    for path_template, path_item in raw.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in SUPPORTED_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            key = _endpoint_key(method, path_template)
            endpoints[key] = (method.lower(), path_template)
    return endpoints


def load_spec_endpoints(spec_path: Path) -> EndpointMap:
    with spec_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict) and "operations" in raw:
        return _load_endpoints_from_cached_spec(raw)

    return _load_endpoints_from_openapi(raw)


def resolve_history_dir(input_dir: Path) -> Path:
    input_dir = input_dir.resolve()
    if input_dir.name == "history":
        return input_dir

    history_dir = input_dir / "history"
    if history_dir.is_dir():
        return history_dir

    raise FileNotFoundError(
        f"Cannot find history directory. Expected either '{input_dir}' to be a history folder or contain a 'history' subfolder."
    )


def resolve_spec_path(input_dir: Path, history_dir: Path, explicit_spec: Optional[Path]) -> Path:
    if explicit_spec:
        return explicit_spec.resolve()

    candidates = [
        input_dir / "specification.json",
        history_dir.parent / "specification.json",
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise FileNotFoundError(
        "Cannot resolve spec file automatically. Provide --spec /path/to/spec.json (or .yaml)."
    )


def iter_har_files(history_dir: Path) -> Iterable[Path]:
    return sorted(history_dir.glob("*.har"))


def collect_500_from_history(history_dir: Path) -> Tuple[Set[str], EvidenceMap, Dict[str, int], int]:
    endpoints_with_500: Set[str] = set()
    first_evidence: EvidenceMap = {}
    total_500_occurrences: Dict[str, int] = {}
    malformed_entries = 0

    for har_file in iter_har_files(history_dir):
        try:
            with har_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            malformed_entries += 1
            continue

        entries = data.get("log", {}).get("entries", [])
        if not isinstance(entries, list):
            malformed_entries += 1
            continue

        for entry in entries:
            endpoint = _normalize_entry_endpoint(entry)
            if endpoint is None:
                malformed_entries += 1
                continue

            status = entry.get("response", {}).get("status")
            if status != 500:
                continue

            endpoints_with_500.add(endpoint)
            total_500_occurrences[endpoint] = total_500_occurrences.get(endpoint, 0) + 1

            if endpoint not in first_evidence:
                first_evidence[endpoint] = (
                    har_file.name,
                    str(entry.get("_id", "")),
                )

    return endpoints_with_500, first_evidence, total_500_occurrences, malformed_entries


def build_rows(
    spec_endpoints: EndpointMap,
    endpoints_with_500: Set[str],
    first_evidence: EvidenceMap,
    total_500_occurrences: Dict[str, int],
) -> List[dict]:
    rows: List[dict] = []

    for endpoint in sorted(spec_endpoints.keys()):
        method, path_template = spec_endpoints[endpoint]
        has_500 = 1 if endpoint in endpoints_with_500 else 0
        evidence_file, evidence_entry = first_evidence.get(endpoint, ("", ""))

        rows.append(
            {
                "endpoint": endpoint,
                "method": method,
                "path_template": path_template,
                "has_500": has_500,
                "first_500_file": evidence_file,
                "first_500_entry_id": evidence_entry,
                "total_500_occurrences": total_500_occurrences.get(endpoint, 0),
            }
        )

    return rows


def write_csv(rows: List[dict], output_csv: Path) -> None:
    fieldnames = [
        "endpoint",
        "method",
        "path_template",
        "has_500",
        "first_500_file",
        "first_500_entry_id",
        "total_500_occurrences",
    ]

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(
    output_summary: Path,
    total_endpoints_in_spec: int,
    total_endpoints_with_500: int,
    malformed_entries: int,
) -> None:
    ratio = 0.0
    if total_endpoints_in_spec > 0:
        ratio = total_endpoints_with_500 / total_endpoints_in_spec

    summary = {
        "total_endpoints_in_spec": total_endpoints_in_spec,
        "total_endpoints_with_500": total_endpoints_with_500,
        "ratio_with_500": ratio,
        "malformed_entries": malformed_entries,
    }

    with output_summary.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def generate_endpoint_500_report(
    input_dir: Path,
    spec_path: Optional[Path] = None,
    output_csv_name: str = "endpoint_500_report.csv",
    output_summary_name: str = "endpoint_500_summary.json",
) -> Tuple[Path, Path, dict]:
    input_dir = input_dir.resolve()
    history_dir = resolve_history_dir(input_dir)
    resolved_spec_path = resolve_spec_path(input_dir, history_dir, spec_path)

    spec_endpoints = load_spec_endpoints(resolved_spec_path)
    endpoints_with_500, first_evidence, total_500_occurrences, malformed_entries = collect_500_from_history(history_dir)

    rows = build_rows(
        spec_endpoints=spec_endpoints,
        endpoints_with_500=endpoints_with_500,
        first_evidence=first_evidence,
        total_500_occurrences=total_500_occurrences,
    )

    output_root = input_dir
    output_csv = output_root / output_csv_name
    output_summary = output_root / output_summary_name

    write_csv(rows, output_csv)

    total_endpoints_with_500 = sum(1 for row in rows if row["has_500"] == 1)
    write_summary(
        output_summary=output_summary,
        total_endpoints_in_spec=len(rows),
        total_endpoints_with_500=total_endpoints_with_500,
        malformed_entries=malformed_entries,
    )

    summary_payload = {
        "total_endpoints_in_spec": len(rows),
        "total_endpoints_with_500": total_endpoints_with_500,
        "malformed_entries": malformed_entries,
    }

    return output_csv, output_summary, summary_payload


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate CSV report: endpoints from spec with has_500 flag from HAR history."
    )
    parser.add_argument(
        "--dir",
        required=True,
        help="Input directory. Accepts either a history folder or a cache folder that contains history/.",
    )
    parser.add_argument(
        "--spec",
        required=False,
        help="Optional path to spec file (OpenAPI JSON or cached specification.json).",
    )
    parser.add_argument(
        "--csv-name",
        default="endpoint_500_report.csv",
        help="Output CSV filename (written inside --dir).",
    )
    parser.add_argument(
        "--summary-name",
        default="endpoint_500_summary.json",
        help="Output summary filename (written inside --dir).",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    output_csv, output_summary, summary = generate_endpoint_500_report(
        input_dir=Path(args.dir),
        spec_path=Path(args.spec) if args.spec else None,
        output_csv_name=args.csv_name,
        output_summary_name=args.summary_name,
    )

    print(f"CSV written to: {output_csv}")
    print(f"Summary written to: {output_summary}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
