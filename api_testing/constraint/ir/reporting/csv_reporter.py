"""
CSV Reporter for constraint extraction outputs.

Generates CSV reports from constraint IR and intermediate JSON outputs.
"""

import csv
import json
from pathlib import Path
from typing import List

from api_testing.constraint.ir.core import ConstraintIRModel, ConstraintModel
from api_testing.constraint.ir.reporting.models import ConstraintCSVRow
from common.logger import get_logger

logger = get_logger(__name__)


class CSVReporter:
    """Generate CSV reports from constraint IR and intermediate outputs.

    Creates per-phase CSV files with detailed constraint information.
    """

    def __init__(self, intermediate_dir: Path, output_dir: Path):
        """Initialize reporter.

        Args:
            intermediate_dir: Directory with intermediate JSON outputs
            output_dir: Directory for CSV output files
        """
        self.intermediate_dir = intermediate_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(
            "Initialized CSVReporter",
            intermediate_dir=str(intermediate_dir),
            output_dir=str(output_dir),
        )

    def generate_all_reports(self, final_ir: ConstraintIRModel):
        """Generate all CSV reports.

        Creates:
        - 1_respropsingle.csv
        - 2_crossfieldresponse.csv
        - 3_requestresponse.csv

        Args:
            final_ir: Final constraint IR model
        """
        logger.info("Generating CSV reports")

        # Generate per-phase CSVs
        self._generate_phase_csv("1_respropsingle", final_ir)
        self._generate_phase_csv("2_crossfieldresponse", final_ir)
        self._generate_phase_csv("3_requestresponse", final_ir)

        logger.info(
            "CSV reports generated",
            output_dir=str(self.output_dir),
            files=[
                "1_respropsingle.csv",
                "2_crossfieldresponse.csv",
                "3_requestresponse.csv",
            ],
        )

    def _generate_phase_csv(self, phase_name: str, ir: ConstraintIRModel):
        """Generate CSV for a specific phase.

        Args:
            phase_name: Phase identifier (e.g., "1_respropsingle")
            ir: Constraint IR model
        """
        rows: list[ConstraintCSVRow] = []

        # Extract constraints for this phase
        for op_id, op_constraints in ir.operation_constraints.items():
            for constraint in op_constraints.constraints:
                # Filter by phase based on source or selector type
                if not self._is_phase_constraint(constraint, phase_name):
                    continue

                # Convert to CSV rows (one row per selector-predicate pair)
                for selector in constraint.selectors:
                    for predicate in constraint.predicates:
                        row = ConstraintCSVRow(
                            operation_id=op_id,
                            field_path=self._extract_field_path(selector.expr),
                            selector_expr=selector.expr,
                            predicate_kind=predicate.kind,
                            predicate_version=predicate.version,
                            args=json.dumps(predicate.args),
                            source_kind=constraint.source.kind,
                            confidence=constraint.source.confidence,
                            evidence=(constraint.source.evidence or "")[:200],
                            constraint_id=constraint.id,
                        )
                        rows.append(row)

        # Write CSV
        csv_file = self.output_dir / f"{phase_name}.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            if not rows:
                # Empty CSV with headers
                writer = csv.DictWriter(
                    f, fieldnames=ConstraintCSVRow.model_fields.keys()
                )
                writer.writeheader()
            else:
                writer = csv.DictWriter(f, fieldnames=rows[0].model_dump().keys())
                writer.writeheader()
                for row in rows:
                    writer.writerow(row.model_dump())

        logger.debug(f"Generated {phase_name}.csv", rows=len(rows))

    @staticmethod
    def _is_phase_constraint(
            constraint: ConstraintModel, phase_name: str
    ) -> bool:
        """Determine if constraint belongs to phase.

        Uses heuristics based on source metadata and selector patterns.

        Args:
            constraint: Constraint to classify
            phase_name: Target phase name

        Returns:
            True if constraint belongs to phase
        """
        # Phase 1: Single-field response (source is structural/description/llm, single selector, response scope)
        if phase_name == "1_respropsingle":
            return (
                len(constraint.selectors) == 1
                and constraint.scope.phase == "response"
                and constraint.source.kind
                in ["schema_structural", "schema_description", "llm", "merged"]
            )

        # Phase 2: Cross-field response (multiple selectors or cross-field source)
        elif phase_name == "2_crossfieldresponse":
            return (
                len(constraint.selectors) > 1
                or "crossfield" in constraint.source.kind.lower()
                or (
                    constraint.scope.phase == "response"
                    and any("cross" in s.expr.lower() for s in constraint.selectors)
                )
            )

        # Phase 3: Request-response (has request_ref selectors)
        elif phase_name == "3_requestresponse":
            return any(s.kind == "request_ref" for s in constraint.selectors)

        return False

    @staticmethod
    def _extract_field_path(selector_expr: str) -> str:
        """Extract clean field path from selector expression.

        Args:
            selector_expr: Full selector expression

        Returns:
            Clean field path

        Examples:
            "$response.body$.items[*].id" -> "items[*].id"
            "$request.query.limit" -> "limit"
        """
        # Response body paths
        if "$response.body$." in selector_expr:
            return selector_expr.split("$response.body$.")[-1]

        # Request paths
        if "$request." in selector_expr:
            parts = selector_expr.split("$request.")[-1]
            # Remove location prefix (query., path., header.)
            if "." in parts:
                return parts.split(".", 1)[-1]
            return parts

        # Fallback: return as-is
        return selector_expr


__all__ = ["CSVReporter"]
