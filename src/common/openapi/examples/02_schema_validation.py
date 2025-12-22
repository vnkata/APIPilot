"""
Example 02: Schema Validation - Validate data against OpenAPI schemas

Demonstrates:
- Validating data against schema components
- Handling validation errors
- Listing available schemas
- Using SchemaValidator
"""

from pathlib import Path

from common.logger import get_logger
from common.openapi import OpenAPIClient
from common.openapi.validation import SchemaValidator

logger = get_logger(__name__)


def example_basic_validation():
    """Basic schema validation"""
    logger.info("=" * 60)
    logger.info("Example 2a: Basic Schema Validation")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)
        validator = SchemaValidator(client.spec)

        # List available schemas
        schemas = validator.list_schemas()
        logger.info(f"\nAvailable Schemas: {schemas}\n")

        # Example: Validate Holiday data
        if "Holiday" in schemas:
            logger.info("Validating 'Holiday' schema:")

            # Valid data
            valid_holiday = {
                "id": 1,
                "date": "2024-01-01",
                "nameEn": "New Year's Day",
                "nameFr": "Jour de l'an",
                "federal": 1,
                "observedDate": "2024-01-01",
            }

            result = validator.validate_data("Holiday", valid_holiday)

            if result.valid:
                logger.info("  ✓ Valid data!")
                logger.info(f"    Data: {valid_holiday}")
            else:
                logger.error(f"  ✗ Validation failed: {result.errors}")
    except Exception as e:
        logger.error(f"Failed to validate schema: {e}")
        return

    logger.info("")


def example_validation_errors():
    """Handle validation errors"""
    logger.info("=" * 60)
    logger.info("Example 2b: Handling Validation Errors")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)
        validator = SchemaValidator(client.spec)

        # Invalid data - missing required fields
        invalid_holiday = {
            "id": 1,
            "date": "2024-01-01",
            # Missing: nameEn, nameFr, federal, observedDate
        }

        logger.info("\nValidating invalid data (missing required fields):")

        result = validator.validate_data("Holiday", invalid_holiday)

        if result.valid:
            logger.info("  ✓ Valid data")
        else:
            logger.warning("  ✗ Validation failed!")
            logger.warning("  Errors:")
            for error in result.errors:
                logger.warning(f"    - {error}")
    except Exception as e:
        logger.error(f"Failed to validate data: {e}")
        return

    logger.info("")


def example_inline_schema_validation():
    """Validate against inline schema dict"""
    logger.info("=" * 60)
    logger.info("Example 2c: Inline Schema Validation")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)
        validator = SchemaValidator(client.spec)

        # Custom inline schema
        user_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["name", "age"],
        }

        # Valid user
        valid_user = {"name": "Alice", "age": 30, "email": "alice@example.com"}

        result = validator.validate_against_schema_dict(user_schema, valid_user)

        logger.info("\nValidating against inline schema:")
        if result.valid:
            logger.info(f"  ✓ Valid user: {valid_user}")
        else:
            logger.error(f"  ✗ Invalid: {result.errors}")

        # Invalid user - age out of range
        invalid_user = {"name": "Bob", "age": 200}

        result = validator.validate_against_schema_dict(user_schema, invalid_user)

        if result.valid:
            logger.info(f"  ✓ Valid user: {invalid_user}")
        else:
            logger.warning(f"  ✗ Invalid user: {result.errors}")
    except Exception as e:
        logger.error(f"Failed to validate inline schema: {e}")
        return

    logger.info("")


def main():
    """Run all schema validation examples"""
    try:
        example_basic_validation()
        example_validation_errors()
        example_inline_schema_validation()

        logger.info("=" * 60)
        logger.info("✓ All schema validation examples completed!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to run examples: {e}")


if __name__ == "__main__":
    main()
