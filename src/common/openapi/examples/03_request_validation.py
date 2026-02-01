"""
Example 03: Request Validation - Validate HTTP requests against spec

Demonstrates:
- Validating HTTP requests (path, query, headers, body)
- Request parameter validation
- Error handling for invalid requests
"""

from pathlib import Path

from common.logger import get_logger
from common.openapi import OpenAPIClient

logger = get_logger(__name__)


def example_validate_get_request():
    """Validate GET request with query parameters"""
    logger.info("=" * 60)
    logger.info("Example 3a: Validate GET Request")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)

        # Valid GET request
        logger.info("\n1. Valid GET /holidays?year=2024:")
        try:
            result = client.validate_request(
                method="GET", path="/holidays", query={"year": 2024}
            )
            logger.info("  ✓ Request valid!")
            logger.info(f"    Parsed query: {result.get('query', {})}")
        except Exception as e:
            logger.error(f"  ✗ Validation failed: {e}")

        # Invalid query parameter (wrong type)
        logger.info("\n2. Invalid GET /holidays?year=invalid:")
        try:
            result = client.validate_request(
                method="GET", path="/holidays", query={"year": "invalid"}
            )
            logger.info(f"  ✓ Request valid: {result}")
        except Exception as e:
            logger.warning(f"  ✗ Validation failed (expected): {type(e).__name__}")
    except Exception as e:
        logger.error(f"Failed to validate GET request: {e}")
        return

    logger.info("")


def example_validate_post_request():
    """Validate POST request with body"""
    logger.info("=" * 60)
    logger.info("Example 3b: Validate POST Request with Body")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)

        # Find POST endpoint (if exists)
        endpoints = client.get_endpoints()
        post_endpoints = [e for e in endpoints if e.method.lower() == "post"]

        if not post_endpoints:
            logger.info("  [INFO] No POST endpoints in this spec")
            logger.info("     (Canada Holidays API is read-only)")
        else:
            endpoint = post_endpoints[0]
            logger.info(f"\nValidating POST {endpoint.path}:")

            # Generate test body from spec
            try:
                test_body = client.generate_request_body(endpoint.path, "POST")
                logger.info(f"  Generated body: {test_body}")

                result = client.validate_request(
                    method="POST", path=endpoint.path, body=test_body
                )
                logger.info("  ✓ Request valid!")
            except Exception as e:
                logger.info(f"  [INFO] {e}")
    except Exception as e:
        logger.error(f"Failed to validate POST request: {e}")
        return

    logger.info("")


def example_validate_path_parameters():
    """Validate path parameters"""
    logger.info("=" * 60)
    logger.info("Example 3c: Validate Path Parameters")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)

        # Find endpoint with path parameters
        endpoints = client.get_endpoints()
        param_endpoints = [e for e in endpoints if "{" in e.path]

        if param_endpoints:
            endpoint = param_endpoints[0]
            logger.info(f"\nValidating {endpoint.method.upper()} {endpoint.path}:")

            # Extract parameter name
            path_param = endpoint.path.split("{")[1].split("}")[0]

            # Valid request
            actual_path = endpoint.path.replace(f"{{{path_param}}}", "1")
            logger.info(f"  Path: {actual_path}")

            try:
                result = client.validate_request(
                    method=endpoint.method, path=actual_path
                )
                logger.info("  ✓ Path parameter valid!")
            except Exception as e:
                logger.info(f"  Note: {e}")
    except Exception as e:
        logger.error(f"Failed to validate path parameters: {e}")
        return

    logger.info("")


def main():
    """Run all request validation examples"""
    try:
        example_validate_get_request()
        example_validate_post_request()
        example_validate_path_parameters()

        logger.info("=" * 60)
        logger.info("✓ All request validation examples completed!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to run examples: {e}")


if __name__ == "__main__":
    main()
