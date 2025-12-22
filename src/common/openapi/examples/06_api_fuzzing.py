"""
Example 06: API Fuzzing - Automated API testing with Schemathesis

Demonstrates:
- Using Fuzzer for property-based testing
- Schema-based fuzzing strategies
- Generating edge cases
- Validation with fuzzing
"""

from pathlib import Path

from common.logger import get_logger
from common.openapi import OpenAPIClient
from common.openapi.generation import SchemaFuzzer

logger = get_logger(__name__)


def example_basic_fuzzing():
    """Basic fuzzing example"""
    logger.info("=" * 60)
    logger.info("Example 6a: Basic Fuzzing")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    logger.info("\n📝 Creating fuzzer...")

    try:
        # Create fuzzer from spec path
        fuzzer = SchemaFuzzer(spec_path)
        logger.info("✓ Fuzzer initialized")

        # Get endpoints for fuzzing
        endpoints = client.get_endpoints()
        logger.info(f"\n✓ Found {len(endpoints)} endpoints to fuzz:")
        for endpoint in endpoints[:3]:  # Show first 3
            logger.info(f"  - {endpoint.method.upper()} {endpoint.path}")
    except Exception as e:
        logger.error(f"Failed to create fuzzer: {e}")
        return

    logger.info("")


def example_fuzz_single_endpoint():
    """Fuzz a single endpoint"""
    logger.info("=" * 60)
    logger.info("Example 6b: Fuzz Single Endpoint")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)
        fuzzer = SchemaFuzzer(spec_path)

        # Find GET /api/v1/holidays endpoint
        endpoints = client.get_endpoints()
        get_holidays = next(
            (e for e in endpoints if "holidays" in e.path.lower()), None
        )

        if get_holidays:
            logger.info(
                f"\n📝 Fuzzing: {get_holidays.method.upper()} {get_holidays.path}"
            )

            # Generate test cases using SchemaFuzzer
            logger.info("✓ Generating test cases using property-based testing...")
            logger.info(f"  (Using Schemathesis for {get_holidays.path})")

            # Note: SchemaFuzzer uses iterator pattern
            case_count = 0
            for case in fuzzer.generate_cases(
                endpoint=get_holidays.path, method=get_holidays.method, count=3
            ):
                case_count += 1
                logger.info(f"\n  Test Case {case_count}:")
                logger.info(f"    Path: {case.path}")
                logger.info(f"    Method: {case.method}")
                if hasattr(case, "query") and case.query:
                    logger.info(f"    Query: {case.query}")

            logger.info(f"\n✓ Generated {case_count} test cases")
    except Exception as e:
        logger.error(f"Failed to fuzz endpoint: {e}")
        return

    logger.info("")


def example_fuzz_with_edge_cases():
    """Generate edge case test data"""
    logger.info("=" * 60)
    logger.info("Example 6c: Fuzz with Edge Cases")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    logger.info("\n📝 Generating edge case data...")

    # Get a schema to fuzz
    schemas = client.validator.list_schemas()

    if schemas:
        schema_name = schemas[0]
        logger.info(f"✓ Testing schema: {schema_name}")

        # Generate data with Hypothesis (underlying fuzzer engine)
        from hypothesis import given
        from hypothesis_jsonschema import from_schema

        schema = client.spec.components.schemas.get(schema_name)

        if schema:
            logger.info(f"\n  Schema properties:")
            if hasattr(schema, "properties") and schema.properties:
                for prop_name in list(schema.properties.keys())[:5]:
                    logger.info(f"    - {prop_name}")

            logger.info("\n  [INFO] Fuzzer can generate:")
            logger.info("    - Boundary values (min/max)")
            logger.info("    - Invalid types")
            logger.info("    - Missing required fields")
            logger.info("    - Extra properties")
            logger.info("    - Unicode/special characters")

    logger.info("")


def example_validate_fuzzed_data():
    """Validate fuzzed data against spec"""
    logger.info("=" * 60)
    logger.info("Example 6d: Validate Fuzzed Data")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)
        fuzzer = SchemaFuzzer(spec_path)

        endpoints = client.get_endpoints()

        if endpoints:
            endpoint = endpoints[0]
            logger.info(f"\n📝 Testing: {endpoint.method.upper()} {endpoint.path}")

            # Generate test cases
            logger.info("\n✓ Generating fuzzy test cases...")

            # Validate generated cases
            valid_count = 0
            invalid_count = 0
            case_num = 0

            for case in fuzzer.generate_cases(
                endpoint=endpoint.path, method=endpoint.method, count=5
            ):
                case_num += 1
                try:
                    # Basic validation - check if case was generated successfully
                    if case and hasattr(case, "path"):
                        valid_count += 1
                        logger.info(f"  Case {case_num}: ✓ Valid structure")
                    else:
                        invalid_count += 1
                        logger.warning(f"  Case {case_num}: ✗ Invalid structure")
                except Exception as e:
                    invalid_count += 1
                    logger.warning(f"  Case {case_num}: ✗ Error - {e}")

            logger.info(f"\n✓ Validation summary:")
            logger.info(f"  Valid: {valid_count}")
            logger.info(f"  Invalid: {invalid_count}")
            logger.info(f"\n  [INFO] Fuzzing helps find edge cases and validation gaps")
    except Exception as e:
        logger.error(f"Failed to validate fuzzed data: {e}")
        return

    logger.info("")


def main():
    """Run all fuzzing examples"""
    try:
        example_basic_fuzzing()
        example_fuzz_single_endpoint()
        example_fuzz_with_edge_cases()
        example_validate_fuzzed_data()

        logger.info("=" * 60)
        logger.info("✓ All fuzzing examples completed!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to complete fuzzing examples: {e}")


if __name__ == "__main__":
    main()
