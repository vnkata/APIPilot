"""
Example 04: Test Generation - Generate test data from schemas

Demonstrates:
- Generating test data using hypothesis
- Request body generation
- Response body generation
- Parameter generation
"""

from pathlib import Path

from common.logger import get_logger
from common.openapi import OpenAPIClient

logger = get_logger(__name__)


def example_generate_request_body():
    """Generate request body test data"""
    logger.info("=" * 60)
    logger.info("Example 4a: Generate Request Body")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    # Find endpoints with request bodies
    endpoints = client.get_endpoints()
    post_endpoints = [e for e in endpoints if e.request_body is not None]

    if not post_endpoints:
        logger.info("  [INFO] No endpoints with request bodies in this spec")
        logger.info("     (Canada Holidays API is read-only)")
    else:
        endpoint = post_endpoints[0]
        logger.info(f"\nGenerating request body for POST {endpoint.path}:")

        try:
            # Generate 3 test bodies
            bodies = client.generate_request_body(endpoint.path, "POST", count=3)

            for i, body in enumerate(bodies, 1):
                logger.info(f"  {i}. {body}")
        except Exception as e:
            logger.error(f"Failed to generate request body: {e}")

    logger.info("")


def example_generate_response_body():
    """Generate response body test data"""
    logger.info("=" * 60)
    logger.info("Example 4b: Generate Response Body")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    # Use GET /api/v1/holidays endpoint
    endpoint = client.find_operation(path="/api/v1/holidays", method="GET")

    logger.info(f"\nGenerating response body for GET {endpoint.path}:")

    try:
        # Generate 3 response bodies
        responses = client.generate_response_body(
            endpoint.path, "GET", status_code="200", count=3
        )

        for i, response in enumerate(responses, 1):
            logger.info(f"  {i}. {response}")
            if i == 1 and isinstance(response, list):
                logger.info(f"     (Array with {len(response)} items)")
    except Exception as e:
        logger.error(f"Failed to generate response body: {e}")

    logger.info("")


def example_generate_parameters():
    """Generate query/path parameters"""
    logger.info("=" * 60)
    logger.info("Example 4c: Generate Parameters")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    # Use GET /holidays endpoint (has query parameters)
    endpoint = client.find_operation(path="/holidays", method="GET")

    logger.info(f"\nGenerating parameters for GET {endpoint.path}:")

    try:
        # Generate query parameters
        query_params = client.generate_parameters(
            endpoint.path, "GET", location="query"
        )

        logger.info(f"  Query parameters: {query_params}")

        # Generate all parameters
        all_params = client.generate_parameters(endpoint.path, "GET")
        logger.info(f"  All parameters: {all_params}")
    except Exception as e:
        logger.error(f"Failed to generate parameters: {e}")

    logger.info("")


def example_generate_from_schema():
    """Generate data from specific schema"""
    logger.info("=" * 60)
    logger.info("Example 4d: Generate from Schema Component")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    # List available schemas
    schemas = client.get_schemas()
    logger.info(f"\nAvailable Schemas: {list(schemas.keys())}\n")

    # Generate from Holiday schema (if exists)
    if "Holiday" in schemas:
        schema = client.get_schema_info("Holiday")
        logger.info("Generating data from 'Holiday' schema:")
        logger.info(f"  Properties: {list(schema.properties.keys())}")

        try:
            # Use test generator directly
            from common.openapi.generation import TestDataGenerator

            generator = TestDataGenerator(client.spec)
            test_data = generator.generate_from_schema(schema.schema, count=2)

            for i, data in enumerate(test_data, 1):
                logger.info(f"  {i}. {data}")
        except Exception as e:
            logger.error(f"Failed to generate from schema: {e}")

    logger.info("")


def main():
    """Run all test generation examples"""
    try:
        example_generate_request_body()
        example_generate_response_body()
        example_generate_parameters()
        example_generate_from_schema()

        logger.info("=" * 60)
        logger.info("✓ All test generation examples completed!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to complete test generation examples: {e}")


if __name__ == "__main__":
    main()
