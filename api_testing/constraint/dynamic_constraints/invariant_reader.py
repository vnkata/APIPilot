from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

from api_testing.constraint.dynamic_constraints.invariant_extractor import (
    EXPECTED_INVARIANTS_HEADER,
)
from api_testing.utils.log import getLogger


@dataclass(frozen=True, slots=True)
class InvariantRecord:
    """A single invariant row produced by the modified Daikon CSV exporter."""

    pptname: str
    invariant: str
    invariant_type: str
    variables: str
    postman_assertion: str


class InvariantReader:
    """Read invariants produced by Daikon from a CSV file."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.logger = getLogger(__name__)

    def read_invariants(self, file_path: str | Path | None = None) -> List[InvariantRecord]:
        """Read invariants from a CSV file and return structured records."""
        resolved_path = Path(file_path) if file_path is not None else self._default_invariants_path()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Invariants file not found: {resolved_path}")

        with resolved_path.open("r", encoding="utf-8", newline="") as invariants_file:
            header_line = invariants_file.readline().rstrip("\r\n")
            if header_line != EXPECTED_INVARIANTS_HEADER:
                raise RuntimeError(
                    "Unexpected invariants CSV header. "
                    f"Expected '{EXPECTED_INVARIANTS_HEADER}' but got '{header_line}'."
                )

            reader = csv.reader(invariants_file, delimiter=";")
            records = [
                self._row_to_record(row)
                for row in reader
                if row
            ]

        self.logger.info("Read %d invariant record(s) from %s", len(records), resolved_path)
        return records

    @staticmethod
    def _row_to_record(row: list[str]) -> InvariantRecord:
        normalized_row = row + [""] * max(0, 5 - len(row))
        return InvariantRecord(
            pptname=normalized_row[0],
            invariant=normalized_row[1],
            invariant_type=normalized_row[2],
            variables=normalized_row[3],
            postman_assertion=normalized_row[4],
        )

    def _default_invariants_path(self) -> Path:
        if self.cache_dir is None:
            raise ValueError("cache_dir is required when file_path is not provided.")
        return self.cache_dir / "invariants.csv"
