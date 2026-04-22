from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api_testing.constraint.dynamic_constraints.invariant_classifier import (  # noqa: E402
    InvariantClassifier,
)
from api_testing.dataset.specification_parser import SpecificationParser  # noqa: E402
from api_testing.models.llms.openai_model import OpenAIModel  # noqa: E402


DATASET_TO_CACHE_DIR: dict[str, str] = {
    "datasets/Bills-api.json": ".cache/Bills API_3",
    "datasets/CanadaHoliday.json": ".cache/Canada Holidays API_3",
    "datasets/GitLabBranch.json": ".cache/GitLab Branch API_1",
    "datasets/GitLabCommit.json": ".cache/GitLab Commit API_2",
    "datasets/GitLabGroups.json": ".cache/GitLab Groups API_3",
    "datasets/GitLabIssues.json": ".cache/GitLab Issues API_4",
    "datasets/GitLabProject.json": ".cache/GitLab Project API_4",
    "datasets/GitLabRepository.json": ".cache/GitLab Repository API_4",
}

MODEL_NAME = "gpt-4.1-mini"
OUTPUT_FILENAME = "classified_invariants.live.csv"
SUMMARY_JSON_FILENAME = "classified_invariants.live.summary.json"
SUMMARY_CSV_FILENAME = "classified_invariants.live.summary.csv"
PERSIST_DEBUG_ARTIFACTS = True
RESUME = True
MAX_WORKERS = 4
MAX_ROWS: int | None = None
LIMIT: int | None = None


def run_one(
    *,
    spec_path: str | Path,
    cache_dir: str | Path,
    model_name: str = MODEL_NAME,
    output_filename: str = OUTPUT_FILENAME,
    summary_json_filename: str = SUMMARY_JSON_FILENAME,
    summary_csv_filename: str = SUMMARY_CSV_FILENAME,
    limit: int | None = LIMIT,
    max_rows: int | None = MAX_ROWS,
    resume: bool = RESUME,
    max_workers: int = MAX_WORKERS,
    persist_debug_artifacts: bool = PERSIST_DEBUG_ARTIFACTS,
) -> Path:
    """Run live invariant classification for one existing cache directory."""
    resolved_spec_path = Path(spec_path)
    resolved_cache_dir = Path(cache_dir)
    output_path = resolved_cache_dir / output_filename
    summary_json_path = resolved_cache_dir / summary_json_filename
    summary_csv_path = resolved_cache_dir / summary_csv_filename

    spec = SpecificationParser(spec_path=str(resolved_spec_path))
    spec.parse_specification()

    model = OpenAIModel(model=model_name)
    classifier = InvariantClassifier(
        spec_parser=spec,
        model=model,
        cache_dir=resolved_cache_dir,
    )

    if limit is None:
        input_path = resolved_cache_dir / "invariants.csv"
        return classifier.classify_invariants(
            input_path=input_path,
            output_path=output_path,
            persist_debug_artifacts=persist_debug_artifacts,
            resume=resume,
            max_workers=max_workers,
            max_rows=max_rows,
            summary_json_path=summary_json_path,
            summary_csv_path=summary_csv_path,
        )

    with tempfile.TemporaryDirectory(prefix="invariant_classifier_live_") as temp_dir:
        sample_path = Path(temp_dir) / "invariants.sample.csv"
        _write_limited_invariants(
            source_path=resolved_cache_dir / "invariants.csv",
            output_path=sample_path,
            limit=limit,
        )
        return classifier.classify_invariants(
            input_path=sample_path,
            output_path=output_path,
            persist_debug_artifacts=persist_debug_artifacts,
            resume=resume,
            max_workers=max_workers,
            max_rows=max_rows,
            summary_json_path=summary_json_path,
            summary_csv_path=summary_csv_path,
        )


def main() -> int:
    failures: list[tuple[str, Exception]] = []
    successes: list[tuple[str, Path]] = []

    print(f"Running live invariant classifier with model={MODEL_NAME}")
    print(f"Output filename: {OUTPUT_FILENAME}")
    print(f"Persist debug artifacts: {PERSIST_DEBUG_ARTIFACTS}")
    print(f"Resume from output CSV: {RESUME}")
    print(f"Max workers: {MAX_WORKERS}")
    print(f"Max rows: {MAX_ROWS if MAX_ROWS is not None else 'all selected rows'}")
    print(f"Limit per cache: {LIMIT if LIMIT is not None else 'all invariants'}")
    print("Note: this performs one live LLM request per invariant row.")

    for spec_path, cache_dir in DATASET_TO_CACHE_DIR.items():
        invariant_count = _count_invariant_rows(Path(cache_dir) / "invariants.csv")
        print(
            f"\nProcessing {spec_path} -> {cache_dir} ({invariant_count} invariant row(s))"
        )
        try:
            output_path = run_one(
                spec_path=spec_path,
                cache_dir=cache_dir,
                model_name=MODEL_NAME,
                output_filename=OUTPUT_FILENAME,
                summary_json_filename=SUMMARY_JSON_FILENAME,
                summary_csv_filename=SUMMARY_CSV_FILENAME,
                limit=LIMIT,
                max_rows=MAX_ROWS,
                resume=RESUME,
                max_workers=MAX_WORKERS,
                persist_debug_artifacts=PERSIST_DEBUG_ARTIFACTS,
            )
        except Exception as exc:  # pragma: no cover - exercised by script mode
            failures.append((cache_dir, exc))
            print(f"FAILED: {cache_dir} -> {type(exc).__name__}: {exc}")
            continue

        successes.append((cache_dir, output_path))
        print(f"SUCCESS: {output_path}")

    print("\nSummary:")
    for cache_dir, output_path in successes:
        print(f"- SUCCESS: {cache_dir} -> {output_path}")
    for cache_dir, exc in failures:
        print(f"- FAILED: {cache_dir} -> {type(exc).__name__}: {exc}")

    return 1 if failures else 0


def _write_limited_invariants(
    *,
    source_path: Path,
    output_path: Path,
    limit: int,
) -> None:
    if limit < 1:
        raise ValueError("limit must be >= 1 when provided.")
    if not source_path.exists():
        raise FileNotFoundError(f"Invariants file not found: {source_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with source_path.open("r", encoding="utf-8", newline="") as source_file:
        header = source_file.readline()
        if not header:
            raise RuntimeError(f"Invariants file is empty: {source_path}")

        reader = csv.reader(source_file, delimiter=";")
        with output_path.open("w", encoding="utf-8", newline="") as output_file:
            output_file.write(header)
            writer = csv.writer(output_file, delimiter=";", lineterminator="\n")
            written = 0
            for row in reader:
                if not row:
                    continue
                if written >= limit:
                    break
                writer.writerow(row)
                written += 1


def _count_invariant_rows(path: Path) -> int | str:
    if not path.exists():
        return "missing"

    with path.open("r", encoding="utf-8", newline="") as invariants_file:
        invariants_file.readline()
        return sum(1 for row in csv.reader(invariants_file, delimiter=";") if row)


if __name__ == "__main__":
    raise SystemExit(main())
