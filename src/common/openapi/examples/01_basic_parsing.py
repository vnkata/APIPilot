"""
Example 01: Basic Parsing - Load and parse OpenAPI specifications

Demonstrates:
- Loading specs from files (JSON/YAML)
- Auto-detection of Swagger 2.0 vs OpenAPI 3.x
- Automatic Swagger 2.0 → OpenAPI 3.x conversion
- Accessing spec metadata
"""

from common import find_project_root
from common.logger import get_logger
from common.openapi import OpenAPIClient

project_root = find_project_root()

openapi_data_path = project_root / "data" / "openapi_datasets"
dataset_name = "JSON Placeholder"


logger = get_logger(__name__)


def example_parse_openapi_3():
    """Parse an OpenAPI 3.x specification"""
    logger.info("=" * 60)
    logger.info("Example 1a: Parse OpenAPI 3.x Spec")
    logger.info("=" * 60)

    # Use Canada Holidays API (OpenAPI 3.x)
    spec_path = openapi_data_path / dataset_name / "openapi.json"

    if not spec_path.exists():
        logger.error(f"⚠️  Spec not found: {spec_path}")
        logger.info("   Please run from project root directory")
        return

    # Parse spec
    try:
        client = OpenAPIClient.from_file(spec_path)
    except Exception as e:
        logger.error(f"Failed to parse spec: {e}")
        return

    # Access metadata
    logger.info(f"\n✓ Title: {client.spec.info.title}")
    logger.info(f"✓ Version: {client.spec.info.version}")
    logger.info(f"✓ OpenAPI Version: {client.spec.openapi}")

    # Get server URL
    base_url = client.introspector.get_base_url()
    logger.info(f"✓ Base URL: {base_url}")

    # Count endpoints
    endpoints = client.get_endpoints()
    logger.info(f"✓ Total Endpoints: {len(endpoints)}")

    for endpoint in endpoints[:3]:  # Show first 3
        logger.info(f"  - {endpoint.method.upper():6} {endpoint.path}")

    logger.info("")


def example_parse_swagger_2():
    """Parse a Swagger 2.0 spec (auto-converted to OpenAPI 3.x)"""
    logger.info("=" * 60)
    logger.info("Example 1b: Parse Swagger 2.0 Spec (Auto-Conversion)")
    logger.info("=" * 60)

    # Use GitLab Branch API (Swagger 2.0)
    spec_path = openapi_data_path / "GitLab Branch" / "openapi.json"

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        # Parse spec - automatically detects and converts Swagger 2.0
        client = OpenAPIClient.from_file(spec_path)

        logger.info(f"\n✓ Title: {client.spec.info.title}")
        logger.info(f"✓ OpenAPI Version: {client.spec.openapi}")
        logger.info("✓ Auto-converted from Swagger 2.0 ✓")

        endpoints = client.get_endpoints()
        logger.info(f"✓ Total Endpoints: {len(endpoints)}")
    except Exception as e:
        logger.error(f"Failed to parse Swagger 2.0 spec: {e}")
        return

    logger.info("")


def example_spec_info():
    """Access detailed spec information"""
    logger.info("=" * 60)
    logger.info("Example 1c: Access Spec Metadata")
    logger.info("=" * 60)

    spec_path = openapi_data_path / dataset_name / "openapi.json"

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    try:
        client = OpenAPIClient.from_file(spec_path)

        # Get comprehensive spec info
        spec_info = client.get_spec_info()

        logger.info("\nSpec Information:")
        logger.info(f"✓ Title: {spec_info['title']}")
        logger.info(f"✓ Version: {spec_info['version']}")
        logger.info(f"✓ Endpoints: {spec_info['total_endpoints']}")
        logger.info(f"✓ Schemas: {spec_info['total_schemas']}")
        logger.info(
            f"✓ Tags: {', '.join(spec_info['tags']) if spec_info['tags'] else 'None'}"
        )
    except Exception as e:
        logger.error(f"Failed to get spec info: {e}")
        return

    logger.info("")


def main():
    """Run all basic parsing examples"""
    try:
        example_parse_openapi_3()
        example_parse_swagger_2()
        example_spec_info()

        logger.info("=" * 60)
        logger.info("✓ All basic parsing examples completed!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to run examples: {e}")


if __name__ == "__main__":
    main()
