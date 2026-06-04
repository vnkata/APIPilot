from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import pytest

from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner
from api_testing.constraint.dynamic_constraints.classified_invariant_reader import (
    ClassifiedInvariantReader,
)
from api_testing.constraint.dynamic_constraints.invariant_reader import InvariantReader
from api_testing.dataset.specification_parser import SpecificationParser
from api_testing.utils.log import getLogger


DATASET_TO_CACHE_DIR = {
    "datasets/Bills-api.json": ".cache/Bills API_3",
    "datasets/CanadaHoliday.json": ".cache/Canada Holidays API_3",
    "datasets/GitLabBranch.json": ".cache/GitLab Branch API_1",
    "datasets/GitLabCommit.json": ".cache/GitLab Commit API_2",
    "datasets/GitLabGroups.json": ".cache/GitLab Groups API_3",
    "datasets/GitLabIssues.json": ".cache/GitLab Issues API_4",
    "datasets/GitLabProject.json": ".cache/GitLab Project API_4",
    "datasets/GitLabRepository.json": ".cache/GitLab Repository API_4",
}


class FakeInvariantClassificationModel:
    def generate(self, prompt, system_prompt=None, schema=None):
        if schema is None:
            return "ok", 0

        payload: dict[str, Any] = {
            "verdict": "true-positive",
            "confidence": 0.73,
            "reason": "Synthetic classifier result for integration testing.",
        }
        return schema.model_validate(payload), 0

    def get_model_name(self) -> str:
        return "fake-invariant-classifier"


def run_dynamic_constraint_pipeline(
    dataset_path: str,
    cache_dir: str,
    *,
    model=None,
    classify: bool = False,
) -> dict[str, Path]:
    spec = SpecificationParser(spec_path=dataset_path)
    spec.parse_specification()

    miner = DynamicConstraintMiner(spec_parser=spec, model=model, cache_dir=cache_dir)
    artifacts = (
        miner.mine_and_classify_dynamic_constraints()
        if classify
        else miner.mine_dynamic_constraints()
    )

    if classify:
        reader = ClassifiedInvariantReader(cache_dir=cache_dir)
        records = reader.read_invariants(artifacts["classified_invariants_path"])
    else:
        reader = InvariantReader(cache_dir=cache_dir)
        records = reader.read_invariants(artifacts["invariants_path"])

    if not records:
        raise AssertionError(f"No invariants were produced for dataset {dataset_path}")

    return artifacts


def _quiet_console_logging() -> None:
    logger = getLogger()
    logger.setLevel(logging.ERROR)
    for handler in logger.handlers:
        handler.setLevel(logging.ERROR)


@pytest.mark.skipif(
    os.getenv("RUN_DYNAMIC_CONSTRAINT_MINER") != "1",
    reason="Set RUN_DYNAMIC_CONSTRAINT_MINER=1 to run full dynamic-constraint integration tests.",
)
@pytest.mark.parametrize(
    ("dataset_path", "cache_dir"),
    list(DATASET_TO_CACHE_DIR.items()),
    ids=list(DATASET_TO_CACHE_DIR.keys()),
)
def test_extract_and_read_invariants_for_all_cache_dirs(dataset_path: str, cache_dir: str):
    artifacts = run_dynamic_constraint_pipeline(dataset_path, cache_dir)

    assert artifacts["decls_path"].exists()
    assert artifacts["dtrace_path"].exists()
    assert artifacts["invariants_path"].exists()


@pytest.mark.skipif(
    os.getenv("RUN_DYNAMIC_CONSTRAINT_MINER") != "1",
    reason="Set RUN_DYNAMIC_CONSTRAINT_MINER=1 to run full dynamic-constraint integration tests.",
)
@pytest.mark.parametrize(
    ("dataset_path", "cache_dir"),
    list(DATASET_TO_CACHE_DIR.items()),
    ids=[f"classified:{dataset}" for dataset in DATASET_TO_CACHE_DIR.keys()],
)
def test_extract_classify_and_read_invariants_for_all_cache_dirs(dataset_path: str, cache_dir: str):
    artifacts = run_dynamic_constraint_pipeline(
        dataset_path,
        cache_dir,
        model=FakeInvariantClassificationModel(),
        classify=True,
    )

    assert artifacts["decls_path"].exists()
    assert artifacts["dtrace_path"].exists()
    assert artifacts["invariants_path"].exists()
    assert artifacts["classified_invariants_path"].exists()


def main() -> int:
    _quiet_console_logging()
    failures: list[tuple[str, Exception]] = []
    classify = os.getenv("RUN_DYNAMIC_CONSTRAINT_MINER_CLASSIFY") == "1"
    model = FakeInvariantClassificationModel() if classify else None

    for dataset_path, cache_dir in DATASET_TO_CACHE_DIR.items():
        print(f"Processing {dataset_path} with cache directory {cache_dir}")
        try:
            artifacts = run_dynamic_constraint_pipeline(
                dataset_path,
                cache_dir,
                model=model,
                classify=classify,
            )
            artifact_key = "classified_invariants_path" if classify else "invariants_path"
            print(f"SUCCESS: {artifacts[artifact_key]}")
        except Exception as exc:  # pragma: no cover - exercised via script mode
            failures.append((dataset_path, exc))
            print(f"FAILED: {dataset_path} -> {type(exc).__name__}: {exc}")

    if failures:
        print("\nSummary of failures:")
        for dataset_path, exc in failures:
            print(f"- {dataset_path}: {type(exc).__name__}: {exc}")
        return 1

    if not classify:
        print("\nTip: set RUN_DYNAMIC_CONSTRAINT_MINER_CLASSIFY=1 to exercise classify flow in script mode.")

    print("\nAll datasets completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
