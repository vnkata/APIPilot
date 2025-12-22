"""
Example 08: Constraint Extraction - Extract response properties and request-response mappings to CSV

Demonstrates:
- Extracting property constraints from response schemas
- Extracting request-response endpoint mappings
- Writing constraints to CSV files
- Processing multiple OpenAPI specs in batch
- Validating extracted constraints
"""

from pathlib import Path
from typing import Optional

from common import find_project_root
from common.logger import get_logger
from common.openapi.extraction import (
    ConstraintCSVWriter,
    RequestResponseExtractor,
    ResponseConstraintsExtractor,
)
from common.openapi.parsing import SpecParser
from common.openapi.config import OpenAPIConfig

project_root = find_project_root()

logger = get_logger(__name__)


class ConstraintExtractionPipeline:
    """
    Complete pipeline for extracting and exporting constraints from OpenAPI specs

    Orchestrates:
    1. Loading OpenAPI specs
    2. Extracting property constraints
    3. Extracting endpoint mappings
    4. Writing to CSV files
    5. Validation of output
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        config: Optional[OpenAPIConfig] = None,
    ) -> None:
        """
        Initialize pipeline

        Args:
            output_dir: Directory for CSV output (default: logs/)
            config: OpenAPI configuration
        """
        self.output_dir = Path(output_dir or "src/common/openapi/examples/logs/")
        self.config = config or OpenAPIConfig()
        self.parser = SpecParser(self.config)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.property_constraints_file = (
            self.output_dir / "response_property_constraints.csv"
        )
        self.endpoint_constraints_file = (
            self.output_dir / "request_response_constraints.csv"
        )

    def process_spec(
        self,
        spec_path: Path,
        spec_name: Optional[str] = None,
    ) -> tuple[int, int]:
        """
        Process a single OpenAPI spec and extract constraints

        Args:
            spec_path: Path to OpenAPI spec file
            spec_name: Human-readable name for spec (default: file stem)

        Returns:
            Tuple of (property_constraints_count, endpoint_constraints_count)

        Raises:
            Exception: If spec cannot be parsed or processed
        """
        spec_name = spec_name or spec_path.stem

        logger.info(f"\n{'='*70}")
        logger.info(f"Processing spec: {spec_name}")
        logger.info(f"File: {spec_path}")
        logger.info(f"{'='*70}")

        try:
            # Parse spec
            logger.info(f"Parsing OpenAPI specification...")
            spec_dict = self.parser.parse(spec_path, resolve_refs=True)

            # Extract response property constraints
            logger.info(f"Extracting response property constraints...")
            response_extractor = ResponseConstraintsExtractor(spec_dict, spec_name)
            property_constraints = response_extractor.extract_all_constraints()
            logger.info(
                f"  ✓ Extracted {len(property_constraints)} property constraints"
            )

            # Write property constraints (append mode for multi-spec)
            prop_written = ConstraintCSVWriter.write_property_constraints(
                property_constraints,
                self.property_constraints_file,
                append=True,
            )

            # Extract request-response endpoint mappings
            logger.info(f"Extracting endpoint request-response mappings...")
            endpoint_extractor = RequestResponseExtractor(spec_dict, spec_name)
            endpoint_constraints = endpoint_extractor.extract_all_mappings()
            logger.info(f"  ✓ Extracted {len(endpoint_constraints)} endpoint mappings")

            # Write endpoint constraints (append mode for multi-spec)
            endpoint_written = ConstraintCSVWriter.write_endpoint_constraints(
                endpoint_constraints,
                self.endpoint_constraints_file,
                append=True,
            )

            logger.info(
                f"\n✓ Successfully processed {spec_name}:"
                f"\n  - {prop_written} property constraints"
                f"\n  - {endpoint_written} endpoint mappings"
            )

            return prop_written, endpoint_written

        except Exception as e:
            logger.error(
                f"Failed to process {spec_name}: {e}",
                extra={"error_type": type(e).__name__},
            )
            raise

    def process_all_specs(
        self, specs_dir: Path, pattern: str = "*.json"
    ) -> tuple[int, int, int]:
        """
        Process all OpenAPI specs in a directory

        Args:
            specs_dir: Directory containing OpenAPI specs
            pattern: File pattern to match (default: *.json)

        Returns:
            Tuple of (total_specs, total_property_constraints, total_endpoint_constraints)
        """
        if not specs_dir.exists():
            logger.error(f"Specs directory not found: {specs_dir}")
            return 0, 0, 0

        # Clear output files before processing multiple specs
        for file in [self.property_constraints_file, self.endpoint_constraints_file]:
            if file.exists():
                file.unlink()

        logger.info(f"\n{'='*70}")
        logger.info(f"Starting batch processing of OpenAPI specs")
        logger.info(f"Directory: {specs_dir}")
        logger.info(f"Pattern: {pattern}")
        logger.info(f"{'='*70}\n")

        spec_files = sorted(specs_dir.rglob(pattern))
        logger.info(f"Found {len(spec_files)} spec files")

        total_specs = 0
        total_property_constraints = 0
        total_endpoint_constraints = 0

        for spec_file in spec_files:
            try:
                prop_count, endpoint_count = self.process_spec(spec_file)
                total_specs += 1
                total_property_constraints += prop_count
                total_endpoint_constraints += endpoint_count
            except Exception as e:
                logger.warning(f"Skipped {spec_file.name}: {e}")
                continue

        logger.info(f"\n{'='*70}")
        logger.info(f"Batch processing complete!")
        logger.info(f"{'='*70}")
        logger.info(
            f"Summary:"
            f"\n  • Total specs processed: {total_specs}"
            f"\n  • Total property constraints: {total_property_constraints}"
            f"\n  • Total endpoint mappings: {total_endpoint_constraints}"
            f"\n  • Property constraints CSV: {self.property_constraints_file}"
            f"\n  • Endpoint mappings CSV: {self.endpoint_constraints_file}"
        )

        return total_specs, total_property_constraints, total_endpoint_constraints

    def validate_output(self) -> bool:
        """
        Validate generated CSV files

        Returns:
            True if all files are valid

        Raises:
            Exception: If validation fails
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"Validating output CSV files")
        logger.info(f"{'='*70}\n")

        all_valid = True

        for csv_file in [
            self.property_constraints_file,
            self.endpoint_constraints_file,
        ]:
            if not csv_file.exists():
                logger.warning(f"CSV file not found: {csv_file}")
                all_valid = False
                continue

            try:
                ConstraintCSVWriter.validate_csv_file(csv_file)
            except Exception as e:
                logger.error(f"Validation failed for {csv_file}: {e}")
                all_valid = False

        if all_valid:
            logger.info(f"\n✓ All CSV files are valid and readable")
        else:
            logger.error(f"\n✗ Some CSV files failed validation")

        return all_valid


def example_single_spec():
    """Extract constraints from a single OpenAPI spec"""
    logger.info("=" * 70)
    logger.info("Example 8a: Extract constraints from single spec")
    logger.info("=" * 70)

    spec_path = project_root / "data/openapi_datasets/Canada Holidays/openapi.json"

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    pipeline = ConstraintExtractionPipeline()

    try:
        prop_count, endpoint_count = pipeline.process_spec(spec_path, "Canada Holidays")

        logger.info(f"\n✓ Single spec extraction successful")
        logger.info(f"  - Property constraints: {prop_count}")
        logger.info(f"  - Endpoint mappings: {endpoint_count}")

        # Validate output
        pipeline.validate_output()

    except Exception as e:
        logger.error(f"Single spec extraction failed: {e}")


def example_batch_specs():
    """Extract constraints from all OpenAPI specs in batch"""
    logger.info("=" * 70)
    logger.info("Example 8b: Extract constraints from all specs (batch processing)")
    logger.info("=" * 70)

    specs_dir = project_root / "data/openapi_datasets"

    if not specs_dir.exists():
        logger.warning(f"⚠️  Specs directory not found: {specs_dir}")
        return

    pipeline = ConstraintExtractionPipeline()

    try:
        total_specs, total_props, total_endpoints = pipeline.process_all_specs(
            specs_dir
        )

        logger.info(f"\n✓ Batch processing complete!")
        logger.info(f"  - Total specs: {total_specs}")
        logger.info(f"  - Total property constraints: {total_props}")
        logger.info(f"  - Total endpoint mappings: {total_endpoints}")

        # Validate output
        if pipeline.validate_output():
            logger.info(f"\n✓✓ All validations passed!")
        else:
            logger.warning(f"\n⚠️  Some validations failed, check logs for details")

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")


def example_demonstrate_csv_structure():
    """Show the structure of generated CSV files"""
    logger.info("=" * 70)
    logger.info("Example 8c: Display CSV structure and sample rows")
    logger.info("=" * 70)

    specs_dir = project_root / "data/openapi_datasets"

    if not specs_dir.exists():
        logger.warning(f"⚠️  Specs directory not found: {specs_dir}")
        return

    pipeline = ConstraintExtractionPipeline()

    # Process specs
    pipeline.process_all_specs(specs_dir)

    # Display structure and samples
    logger.info(f"\n📊 Response Property Constraints CSV")
    logger.info(f"   File: {pipeline.property_constraints_file}")
    logger.info(f"   Columns: spec_name, component_name, property_name, property_path,")
    logger.info(f"            type, format, minimum, maximum, min_length, max_length,")
    logger.info(f"            pattern, enum_values, description, is_required,")
    logger.info(f"            default_value, validation_notes")

    # Show first few rows
    try:
        with open(pipeline.property_constraints_file, "r", encoding="utf-8") as f:
            lines = f.readlines()[:5]
            if lines:
                logger.info(f"\n   Sample rows (first 5 lines):")
                for line in lines:
                    logger.info(f"   {line.rstrip()}")
    except Exception as e:
        logger.error(f"Failed to read property constraints file: {e}")

    logger.info(f"\n📊 Request-Response Constraints CSV")
    logger.info(f"   File: {pipeline.endpoint_constraints_file}")
    logger.info(f"   Columns: spec_name, endpoint_path, http_method,")
    logger.info(f"            request_body_component, response_component,")
    logger.info(f"            response_status_code, constraint_notes,")
    logger.info(f"            validation_notes")

    # Show first few rows
    try:
        with open(pipeline.endpoint_constraints_file, "r", encoding="utf-8") as f:
            lines = f.readlines()[:5]
            if lines:
                logger.info(f"\n   Sample rows (first 5 lines):")
                for line in lines:
                    logger.info(f"   {line.rstrip()}")
    except Exception as e:
        logger.error(f"Failed to read endpoint constraints file: {e}")


def run_all_examples():
    """Run all example demonstrations"""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 08: CONSTRAINT EXTRACTION")
    logger.info("=" * 70)

    # Example 8a: Single spec
    example_single_spec()

    # Example 8b: Batch processing
    example_batch_specs()

    # Example 8c: Show CSV structure
    example_demonstrate_csv_structure()

    logger.info("\n" + "=" * 70)
    logger.info("✓ All examples completed successfully!")
    logger.info("=" * 70 + "\n")


if __name__ == "__main__":
    run_all_examples()
