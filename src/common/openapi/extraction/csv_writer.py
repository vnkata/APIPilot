"""
CSV export utilities for constraints

Writes extracted constraints to CSV files with proper formatting.
"""

import csv
from pathlib import Path

from common.logger.utils.helpers import get_logger
from common.openapi.extraction.models import EndpointConstraint, PropertyConstraint

logger = get_logger(__name__)


class ConstraintCSVWriter:
    """
    Write extracted constraints to CSV files

    Features:
    - Write property constraints to CSV
    - Write endpoint mappings to CSV
    - Handle special characters and encoding
    - Automatic header generation
    """

    # CSV Field order for property constraints
    PROPERTY_CONSTRAINT_FIELDS = [
        "spec_name",
        "component_name",
        "property_name",
        "property_path",
        "type",
        "format",
        "minimum",
        "maximum",
        "exclusive_minimum",
        "exclusive_maximum",
        "min_length",
        "max_length",
        "pattern",
        "enum_values",
        "description",
        "is_required",
        "default_value",
        "validation_notes",
    ]

    # CSV Field order for endpoint constraints
    ENDPOINT_CONSTRAINT_FIELDS = [
        "spec_name",
        "endpoint_path",
        "http_method",
        "request_body_component",
        "response_component",
        "response_status_code",
        "constraint_notes",
        "validation_notes",
    ]

    @staticmethod
    def write_property_constraints(
        constraints: list[PropertyConstraint],
        output_path: Path,
        append: bool = False,
    ) -> int:
        """
        Write property constraints to CSV

        Args:
            constraints: List of PropertyConstraint objects
            output_path: Output CSV file path
            append: Whether to append to existing file

        Returns:
            Number of rows written

        Raises:
            IOError: If file cannot be written
        """
        if not constraints:
            logger.info("No property constraints to write")
            return 0

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = output_path.exists() and append
        rows_written = 0

        try:
            with open(
                output_path,
                mode="a" if append else "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.DictWriter(
                    f, fieldnames=ConstraintCSVWriter.PROPERTY_CONSTRAINT_FIELDS
                )

                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()

                for constraint in constraints:
                    writer.writerow(constraint.to_csv_row())
                    rows_written += 1

            logger.info(f"Wrote {rows_written} property constraints to {output_path}")
            return rows_written

        except Exception as e:
            logger.error(f"Failed to write property constraints to {output_path}: {e}")
            raise

    @staticmethod
    def write_endpoint_constraints(
        constraints: list[EndpointConstraint],
        output_path: Path,
        append: bool = False,
    ) -> int:
        """
        Write endpoint constraints to CSV

        Args:
            constraints: List of EndpointConstraint objects
            output_path: Output CSV file path
            append: Whether to append to existing file

        Returns:
            Number of rows written

        Raises:
            IOError: If file cannot be written
        """
        if not constraints:
            logger.info("No endpoint constraints to write")
            return 0

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = output_path.exists() and append
        rows_written = 0

        try:
            with open(
                output_path,
                mode="a" if append else "w",
                newline="",
                encoding="utf-8",
            ) as f:
                writer = csv.DictWriter(
                    f, fieldnames=ConstraintCSVWriter.ENDPOINT_CONSTRAINT_FIELDS
                )

                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()

                for constraint in constraints:
                    writer.writerow(constraint.to_csv_row())
                    rows_written += 1

            logger.info(f"Wrote {rows_written} endpoint constraints to {output_path}")
            return rows_written

        except Exception as e:
            logger.error(f"Failed to write endpoint constraints to {output_path}: {e}")
            raise

    @staticmethod
    def validate_csv_file(csv_path: Path) -> bool:
        """
        Validate CSV file can be read

        Args:
            csv_path: Path to CSV file

        Returns:
            True if file is valid and readable

        Raises:
            IOError: If file cannot be read
        """
        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                row_count = sum(1 for _ in reader)

            logger.info(f"CSV validation passed: {csv_path} ({row_count} rows)")
            return True
        except Exception as e:
            logger.error(f"CSV validation failed for {csv_path}: {e}")
            raise


__all__ = ["ConstraintCSVWriter"]
