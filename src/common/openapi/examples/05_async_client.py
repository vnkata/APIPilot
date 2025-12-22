"""
Example 05: Async Client - Asynchronous HTTP client usage

Demonstrates:
- Using AsyncDynamicHTTPClient
- Async context manager
- Concurrent requests
- Retry logic
"""

import asyncio
from pathlib import Path

from common.logger import get_logger
from common.openapi import OpenAPIClient
from common.openapi.http import AsyncDynamicHTTPClient

logger = get_logger(__name__)


async def example_basic_async_client():
    """Basic async client usage"""
    logger.info("=" * 60)
    logger.info("Example 5a: Basic Async Client")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    logger.info("\n📝 Creating async HTTP client...")

    # Use async context manager
    async with AsyncDynamicHTTPClient(client.spec) as http:
        logger.info(f"✓ Async client created")
        logger.info(f"  Base URL: {http.base_url}")
        logger.info(f"  Retry enabled: {http.enable_retry}")

        # Note: Actual API call would require live server
        # response = await http.request("/holidays", "GET", query_params={"year": 2024})
        # logger.info(f"✓ Response: {response.status_code}")

    logger.info("✓ Client closed")
    logger.info("")


async def example_concurrent_requests():
    """Make concurrent requests"""
    logger.info("=" * 60)
    logger.info("Example 5b: Concurrent Requests")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    logger.info("\n📝 Demonstrating concurrent request pattern...")

    async with AsyncDynamicHTTPClient(client.spec) as http:
        # Example: Concurrent requests for multiple years
        years = [2022, 2023, 2024]

        logger.info(f"✓ Would fetch holidays for {len(years)} years concurrently")

        # Pattern for concurrent requests:
        # tasks = [
        #     http.request("/holidays", "GET", query_params={"year": year})
        #     for year in years
        # ]
        # responses = await asyncio.gather(*tasks)
        # logger.info(f"✓ Received {len(responses)} responses")

        logger.info("  (Requires live API server)")

    logger.info("")


async def example_async_with_retry():
    """Async client with retry logic"""
    logger.info("=" * 60)
    logger.info("Example 5c: Async Client with Retry")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    logger.info("\n📝 Creating async client with retry enabled...")

    # Enable automatic retry (enabled by default)
    async with AsyncDynamicHTTPClient(
        client.spec, enable_retry=True
    ) as http_with_retry:
        logger.info("✓ Retry enabled (max 3 attempts)")
        logger.info("  - Exponential backoff: 1s → 2s → 4s")
        logger.info("  - Retries on: timeouts, 5xx errors")

        # Disable retry for specific use cases
        async with AsyncDynamicHTTPClient(
            client.spec, enable_retry=False
        ) as http_no_retry:
            logger.info("\n✓ Retry disabled (fail fast)")

    logger.info("")


async def example_async_by_operation_id():
    """Request by operation ID"""
    logger.info("=" * 60)
    logger.info("Example 5d: Request by Operation ID")
    logger.info("=" * 60)

    spec_path = Path("RBCTest_dataset/Canada Holidays/openapi.json")

    if not spec_path.exists():
        logger.warning(f"⚠️  Spec not found: {spec_path}")
        return

    client = OpenAPIClient.from_file(spec_path)

    # Find operations with IDs
    endpoints = client.get_endpoints()
    ops_with_ids = [e for e in endpoints if e.operation_id]

    if ops_with_ids:
        endpoint = ops_with_ids[0]
        logger.info(f"\nOperation ID: {endpoint.operation_id}")
        logger.info(f"Path: {endpoint.method.upper()} {endpoint.path}")

        async with AsyncDynamicHTTPClient(client.spec) as http:
            logger.info(f"\n✓ Can call by operation ID:")
            logger.info(
                f"  await http.request_by_operation_id('{endpoint.operation_id}')"
            )
            logger.info("  (Requires live API)")
    else:
        logger.info("\n  [INFO] No operations with IDs in this spec")

    logger.info("")


def main():
    """Run all async client examples"""
    try:
        # Run async examples
        asyncio.run(example_basic_async_client())
        asyncio.run(example_concurrent_requests())
        asyncio.run(example_async_with_retry())
        asyncio.run(example_async_by_operation_id())

        logger.info("=" * 60)
        logger.info("✓ All async client examples completed!")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to complete async client examples: {e}")


if __name__ == "__main__":
    main()
