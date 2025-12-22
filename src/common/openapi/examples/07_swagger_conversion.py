"""
Example 07: Swagger Conversion - Converting Swagger 2.0 to OpenAPI 3.x

Demonstrates:
- Automatic Swagger detection
- Converting Swagger to OpenAPI 3.x
- Accessing converted spec
- Comparing formats
"""

from pathlib import Path
import json

from common.logger import get_logger
from common.openapi import OpenAPIClient
from common.openapi.parsing import SpecParser

logger = get_logger(__name__)


def example_detect_swagger():
    """Detect Swagger 2.0 specs"""
    logger.info("=" * 60)
    logger.info("Example 7a: Detect Swagger Specs")
    logger.info("=" * 60)

    swagger_path = Path("RBCTest_dataset/GitLab Branch/openapi.json")

    if not swagger_path.exists():
        logger.warning(f"⚠️  Spec not found: {swagger_path}")
        return

    logger.info("\n📝 Checking spec format...")

    # Read spec
    with open(swagger_path) as f:
        spec_dict = json.load(f)

    # Check version
    if "swagger" in spec_dict:
        version = spec_dict["swagger"]
        logger.info(f"✓ Detected Swagger {version}")
    elif "openapi" in spec_dict:
        version = spec_dict["openapi"]
        logger.info(f"✓ Detected OpenAPI {version}")
    else:
        logger.warning("⚠️  Unknown spec format")

    logger.info("")


def example_convert_swagger():
    """Convert Swagger to OpenAPI"""
    logger.info("=" * 60)
    logger.info("Example 7b: Convert Swagger → OpenAPI 3.x")
    logger.info("=" * 60)

    swagger_path = Path("RBCTest_dataset/GitLab Branch/openapi.json")

    if not swagger_path.exists():
        logger.warning(f"⚠️  Spec not found: {swagger_path}")
        return

    logger.info("\n📝 Converting Swagger to OpenAPI 3.x...")

    try:
        # SpecParser handles conversion automatically
        # Just load with OpenAPIClient which uses SpecParser internally
        client = OpenAPIClient.from_file(swagger_path)

        logger.info("✓ Swagger 2.0 detected and converted automatically!")
        logger.info(f"✓ Converted to OpenAPI {client.spec.openapi}")

        # Show spec info after conversion
        logger.info("\n  Converted spec info:")
        logger.info(f"    Title: {client.spec.info.title}")
        logger.info(f"    Version: {client.spec.info.version}")
        logger.info(f"    Endpoints: {len(client.get_endpoints())}")

        logger.info("\n  Key changes (automatic):")
        logger.info("    - 'swagger: 2.0' → 'openapi: 3.0.x'")
        logger.info("    - Definitions → components/schemas")
        logger.info("    - Parameters restructured")
        logger.info("    - Security schemes updated")

    except Exception as e:
        logger.error(f"✗ Conversion error: {e}")

    logger.info("")


def example_automatic_conversion():
    """OpenAPIClient handles conversion automatically"""
    logger.info("=" * 60)
    logger.info("Example 7c: Automatic Conversion")
    logger.info("=" * 60)

    swagger_path = Path("RBCTest_dataset/GitLab Branch/openapi.json")

    if not swagger_path.exists():
        logger.warning(f"⚠️  Spec not found: {swagger_path}")
        return

    logger.info("\n📝 Loading Swagger spec with OpenAPIClient...")

    # Client automatically converts Swagger → OpenAPI
    client = OpenAPIClient.from_file(swagger_path)

    logger.info("✓ Spec loaded and converted automatically!")
    logger.info(f"\n  Title: {client.spec.info.title}")
    logger.info(f"  Version: {client.spec.info.version}")
    logger.info(f"  Endpoints: {len(client.get_endpoints())}")

    # Show available operations
    endpoints = client.get_endpoints()
    if endpoints:
        logger.info(f"\n  Sample operations:")
        for endpoint in endpoints[:3]:
            logger.info(f"    {endpoint.method.upper()} {endpoint.path}")

    logger.info("\n  [INFO] No manual conversion needed!")

    logger.info("")


def example_compare_formats():
    """Compare Swagger vs OpenAPI"""
    logger.info("=" * 60)
    logger.info("Example 7d: Format Comparison")
    logger.info("=" * 60)

    logger.info("\n📋 Swagger 2.0 vs OpenAPI 3.x:")
    logger.info("")

    logger.info("  Swagger 2.0:")
    logger.info("    swagger: '2.0'")
    logger.info("    definitions:")
    logger.info("      Pet:")
    logger.info("        type: object")
    logger.info("")

    logger.info("  OpenAPI 3.0:")
    logger.info("    openapi: '3.0.3'")
    logger.info("    components:")
    logger.info("      schemas:")
    logger.info("        Pet:")
    logger.info("          type: object")
    logger.info("")

    logger.info("  Key Differences:")
    logger.info("    ✓ Better request/response definitions")
    logger.info("    ✓ Multiple servers (not just basePath)")
    logger.info("    ✓ Callbacks and links")
    logger.info("    ✓ Enhanced security schemes")
    logger.info("    ✓ requestBody vs parameters")
    logger.info("")

    logger.info("  [INFO] OpenAPIClient supports both formats seamlessly")

    logger.info("")


def main():
    """Run all Swagger conversion examples"""
    try:
        example_detect_swagger()
        example_convert_swagger()
        example_automatic_conversion()
        example_compare_formats()

        logger.info("=" * 60)
        logger.info("✓ All Swagger conversion examples completed!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to complete Swagger conversion examples: {e}")


if __name__ == "__main__":
    main()
