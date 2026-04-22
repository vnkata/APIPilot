from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List

from api_testing.utils.log import getLogger


CLASSIFIED_INVARIANTS_HEADER = (
    "pptname;invariant;invariantType;variables;postmanAssertion;verdict;"
    "confidence;reason;model;promptVersion;examplesCount;approxNumberOfOperations"
)


@dataclass(frozen=True, slots=True)
class ClassifiedInvariantRecord:
    pptname: str
    invariant: str
    invariant_type: str
    variables: str
    postman_assertion: str
    verdict: str
    confidence: float
    reason: str
    model: str
    prompt_version: str
    examples_count: int
    approx_number_of_operations: int


class ClassifiedInvariantReader:
    """Read classified invariants from the classifier CSV artifact."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.logger = getLogger(__name__)

    def read_invariants(
        self,
        file_path: str | Path | None = None,
    ) -> List[ClassifiedInvariantRecord]:
        resolved_path = Path(file_path) if file_path is not None else self._default_path()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Classified invariants file not found: {resolved_path}")

        with resolved_path.open("r", encoding="utf-8", newline="") as invariants_file:
            header_line = invariants_file.readline().rstrip("\r\n")
            if header_line != CLASSIFIED_INVARIANTS_HEADER:
                raise RuntimeError(
                    "Unexpected classified invariants CSV header. "
                    f"Expected '{CLASSIFIED_INVARIANTS_HEADER}' but got '{header_line}'."
                )

            reader = csv.reader(invariants_file, delimiter=";")
            records = [self._row_to_record(row) for row in reader if row]

        self.logger.info(
            "Read %d classified invariant record(s) from %s",
            len(records),
            resolved_path,
        )
        return records

    @staticmethod
    def _row_to_record(row: list[str]) -> ClassifiedInvariantRecord:
        normalized_row = row + [""] * max(0, 12 - len(row))
        return ClassifiedInvariantRecord(
            pptname=normalized_row[0],
            invariant=normalized_row[1],
            invariant_type=normalized_row[2],
            variables=normalized_row[3],
            postman_assertion=normalized_row[4],
            verdict=normalized_row[5],
            confidence=float(normalized_row[6] or 0.0),
            reason=normalized_row[7],
            model=normalized_row[8],
            prompt_version=normalized_row[9],
            examples_count=int(normalized_row[10] or 0),
            approx_number_of_operations=int(normalized_row[11] or 0),
        )

    def _default_path(self) -> Path:
        if self.cache_dir is None:
            raise ValueError("cache_dir is required when file_path is not provided.")
        return self.cache_dir / "classified_invariants.csv"
