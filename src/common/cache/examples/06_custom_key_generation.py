"""
Example 06: Custom Key Generation
Demonstrates using custom key functions for advanced cache key strategies.

Topics:
- Custom key_fn parameter
- Complex object serialization
- Domain-specific cache keys
- Hash-based keys for large data
"""

import json

from common.cache import CacheType
from common.cache.utils.decorators import cache_result
from common.logger import get_logger

logger = get_logger(__name__)


# Example 1: Custom key function for complex objects
def create_user_key(func, args, kwargs):
    """Custom key function for user objects."""
    if args:
        user_id = args[0] if args else kwargs.get("user_id")
        return f"user:{user_id}:profile"
    return "user:unknown"


@cache_result(
    cache_type=CacheType.MEMORY,
    key_fn=create_user_key,
    ttl=3600,
)
def get_user_profile(user_id: int):
    """Fetch user profile with custom key."""
    logger.info(f"  [DB] Loading profile for user {user_id}...")
    return {
        "user_id": user_id,
        "name": f"User_{user_id}",
        "email": f"user{user_id}@example.com",
        "created_at": "2024-01-01",
    }


# Example 2: Custom key based on parameter hashing
def create_data_hash_key(func, args, kwargs):
    """Create key by hashing large data structures."""
    if args:
        data = args[0] if args else kwargs.get("data")
        # Hash the data to create a compact key
        data_str = json.dumps(data, sort_keys=True, default=str)
        import hashlib

        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
        return f"process:{func.__name__}:{data_hash}"
    return f"process:{func.__name__}:unknown"


@cache_result(
    cache_type=CacheType.MEMORY,
    key_fn=create_data_hash_key,
    ttl=1800,
)
def process_data(data: dict):
    """Process data with hash-based cache key."""
    logger.info(f"  [Processing] Computing for {len(data)} items...")
    result = sum(data.get("values", []))
    return {"input_size": len(data), "result": result}


# Example 3: Namespace-based key generation
def create_api_resource_key(func, args, kwargs):
    """Create RESTful resource-based cache key."""
    resource = kwargs.get("resource", "unknown")
    resource_id = kwargs.get("resource_id", "unknown")
    return f"api:rest:{resource}:{resource_id}:data"


@cache_result(
    cache_type=CacheType.MEMORY,
    key_fn=create_api_resource_key,
    ttl=600,
)
def fetch_api_resource(resource: str = None, resource_id: str = None):
    """Fetch REST API resource with custom key."""
    logger.info(f"  [API] GET /api/{resource}/{resource_id}")
    return {
        "resource": resource,
        "id": resource_id,
        "data": f"{resource}_{resource_id}_data",
    }


# Example 4: Time-aware cache key
def create_time_based_key(func, args, kwargs):
    """Create key that includes date for daily cache rotation."""
    from datetime import datetime

    date_str = datetime.now().strftime("%Y-%m-%d")
    metric_name = args[0] if args else kwargs.get("metric")
    return f"metrics:{metric_name}:{date_str}"


@cache_result(
    cache_type=CacheType.MEMORY,
    key_fn=create_time_based_key,
    ttl=86400,  # 1 day
)
def get_daily_metric(metric: str):
    """Get daily metric (cache rotates daily)."""
    logger.info(f"  [Metrics] Computing {metric}...")
    return {"metric": metric, "value": 42, "unit": "count"}


def example_1_custom_user_key():
    """Custom key for user data."""
    logger.info("=" * 70)
    logger.info("Example 6.1: Custom User Key")
    logger.info("=" * 70)

    # First call - computes and caches
    logger.info("▶ First call: get_user_profile(1)")
    logger.info("  Generated key: 'user:1:profile'")
    user1 = get_user_profile(1)
    logger.info(f"✓ Result: {user1}\n")

    # Second call - uses cached result
    logger.info("▶ Second call: get_user_profile(1) [CACHED]")
    user1_cached = get_user_profile(1)
    logger.info(f"✓ Result (from cache): {user1_cached}\n")

    print()


def example_2_hash_based_key():
    """Hash-based key for complex data."""
    logger.info("=" * 70)
    logger.info("Example 6.2: Hash-Based Key for Large Data")
    logger.info("=" * 70)

    data1 = {"values": [1, 2, 3, 4, 5]}

    logger.info("▶ First call: process_data({'values': [1,2,3,4,5]})")
    logger.info("  Generated key based on data hash: 'process:process_data:XXXXX'")
    result1 = process_data(data1)
    logger.info(f"✓ Result: {result1}\n")

    # Same data - returns cached result
    logger.info("▶ Second call with same data [CACHED]")
    result1_cached = process_data(data1)
    logger.info(f"✓ Result (from cache): {result1_cached}\n")

    # Different data - new result
    data2 = {"values": [10, 20, 30]}
    logger.info("▶ Third call with different data")
    logger.info("  Different hash → different cache key → new computation")
    result2 = process_data(data2)
    logger.info(f"✓ Result: {result2}\n")

    print()


def example_3_restful_key():
    """RESTful resource-based key."""
    logger.info("=" * 70)
    logger.info("Example 6.3: RESTful Resource-Based Key")
    logger.info("=" * 70)

    # Fetch users
    logger.info("▶ fetch_api_resource(resource='users', resource_id='123')")
    logger.info("  Generated key: 'api:rest:users:123:data'")
    result1 = fetch_api_resource(resource="users", resource_id="123")
    logger.info(f"✓ Result: {result1}\n")

    # Fetch posts
    logger.info("▶ fetch_api_resource(resource='posts', resource_id='456')")
    logger.info("  Generated key: 'api:rest:posts:456:data'")
    result2 = fetch_api_resource(resource="posts", resource_id="456")
    logger.info(f"✓ Result: {result2}\n")

    # Fetch same user again
    logger.info("▶ fetch_api_resource(resource='users', resource_id='123') [CACHED]")
    result3 = fetch_api_resource(resource="users", resource_id="123")
    logger.info(f"✓ Result (from cache): {result3}\n")

    print()


def example_4_time_aware_key():
    """Time-aware cache key (daily rotation)."""
    logger.info("=" * 70)
    logger.info("Example 6.4: Time-Aware Cache Key (Daily Rotation)")
    logger.info("=" * 70)

    from datetime import datetime

    current_date = datetime.now().strftime("%Y-%m-%d")

    logger.info("▶ get_daily_metric('cpu_usage')")
    logger.info(f"  Generated key: 'metrics:cpu_usage:{current_date}'")
    metric1 = get_daily_metric("cpu_usage")
    logger.info(f"✓ Result: {metric1}\n")

    logger.info("▶ get_daily_metric('cpu_usage') [CACHED]")
    logger.info("  Same date → same cache key → cached result")
    metric2 = get_daily_metric("cpu_usage")
    logger.info(f"✓ Result (from cache): {metric2}\n")

    logger.info(
        "  Note: Tomorrow, the date changes → new cache key → fresh computation\n"
    )

    print()


def example_5_comparison_default_vs_custom():
    """Compare default key generation with custom."""
    logger.info("=" * 70)
    logger.info("Example 6.5: Default vs Custom Key Generation")
    logger.info("=" * 70)

    logger.info("Default key generation:")
    logger.info("  Pattern: '{module}.{function}|args:...|kwargs:...'")
    logger.info("  Example: 'common.cache.examples.fetch_user|args:(123,)'")
    logger.info("  Pros: Generic, works everywhere")
    logger.info("  Cons: Long, not human-readable, includes internals")
    logger.info("")

    logger.info("Custom key generation:")
    logger.info("  Pattern: Domain-specific (you define)")
    logger.info("  Example: 'user:123:profile'")
    logger.info("  Pros: Short, readable, domain-appropriate")
    logger.info("  Cons: Requires custom logic for each use case")
    logger.info("")

    logger.info("✓ Choose custom when:")
    logger.info("  - You have domain-specific naming conventions")
    logger.info("  - You need short, human-readable keys (e.g., for manual inspection)")
    logger.info("  - You have special requirements (hashing, date-based, etc.)")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 06: Custom Key Generation")
    logger.info("=" * 70 + "\n")

    try:
        example_1_custom_user_key()
        example_2_hash_based_key()
        example_3_restful_key()
        example_4_time_aware_key()
        example_5_comparison_default_vs_custom()

        logger.info("=" * 70)
        logger.info("✓ All custom key generation examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
