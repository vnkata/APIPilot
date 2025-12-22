"""
Example 02: Redis Cache
Demonstrates caching with Redis backend for distributed/persistent caching.

Topics:
- Connecting to Redis
- Redis cache operations (set, get, delete)
- Serialization (JSON, Pickle)
- Key prefixes for namespacing
- Health checks and connection verification
"""

from common.cache import CacheFactory, CacheType
from common.logger import get_logger

logger = get_logger(__name__)


def example_1_redis_basic_operations():
    """Basic Redis cache operations."""
    logger.info("=" * 70)
    logger.info("Example 2.1: Basic Redis Cache Operations")
    logger.info("=" * 70)

    try:
        # Create Redis cache (requires Redis running on localhost:6379)
        cache = CacheFactory.create_redis_cache(
            host="localhost",
            port=6379,
            db=0,
            serialization="json",
        )

        logger.info(f"✓ Connected to Redis: {type(cache).__name__}")

        # Set values
        cache.set("user:1:profile", {"name": "Alice", "email": "alice@example.com"})
        cache.set("user:2:profile", {"name": "Bob", "email": "bob@example.com"})

        logger.info("✓ Stored 2 user profiles in Redis")

        # Get values
        profile1 = cache.get("user:1:profile")
        logger.info(f"✓ Retrieved profile: {profile1}")

        # Check existence
        exists = cache.exists("user:1:profile")
        logger.info(f"✓ Key exists: {exists}")

        # Delete value
        deleted = cache.delete("user:2:profile")
        logger.info(f"✓ Deleted user:2:profile: {deleted}")

    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")
        logger.info("   Skipping Redis examples (ensure Redis is running)")

    print()


def example_2_redis_with_ttl():
    """Redis cache with expiration."""
    logger.info("=" * 70)
    logger.info("Example 2.2: Redis with TTL (Expiration)")
    logger.info("=" * 70)

    try:
        cache = CacheFactory.create_redis_cache()

        # Store session token with 1-hour expiration
        cache.set("session:user123", "token_xyz", ttl=3600)
        logger.info("✓ Stored session token with 1-hour TTL")

        # Retrieve immediately
        token = cache.get("session:user123")
        logger.info(f"✓ Retrieved session token: {token}")

        # Check TTL remaining (if available)
        remaining = cache.get("session:user123")
        logger.info(f"✓ Token still valid: {remaining is not None}")

    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")

    print()


def example_3_redis_with_key_prefix():
    """Using key prefixes for namespacing."""
    logger.info("=" * 70)
    logger.info("Example 2.3: Redis with Key Prefix Namespacing")
    logger.info("=" * 70)

    try:
        # Create cache with key prefix
        cache = CacheFactory.create_redis_cache(
            key_prefix="myapp:cache:",
            serialization="json",
        )

        logger.info("✓ Created Redis cache with prefix 'myapp:cache:'")

        # Store values (prefix will be added automatically)
        cache.set("config:version", "1.0.0")
        cache.set("config:debug", True)

        logger.info("✓ Stored configuration values")
        logger.info("  (Actual keys in Redis: 'myapp:cache:config:version', etc.)")

        # Retrieve values
        version = cache.get("config:version")
        debug = cache.get("config:debug")

        logger.info(f"✓ Retrieved: version={version}, debug={debug}")

    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")

    print()


def example_4_redis_different_serialization():
    """Using different serialization methods."""
    logger.info("=" * 70)
    logger.info("Example 2.4: Different Serialization Methods")
    logger.info("=" * 70)

    try:
        # JSON serialization (human-readable, standard)
        cache_json = CacheFactory.create_redis_cache(
            serialization="json",
        )

        # Pickle serialization (more compact, Python-specific)
        cache_pickle = CacheFactory.create_redis_cache(
            db=1,  # Use different database
            serialization="pickle",
        )

        test_data = {"items": [1, 2, 3], "nested": {"key": "value"}}

        # Store with both methods
        cache_json.set("test:json", test_data)
        cache_pickle.set("test:pickle", test_data)

        logger.info("✓ Stored same data with JSON and Pickle serialization")

        # Retrieve
        json_result = cache_json.get("test:json")
        pickle_result = cache_pickle.get("test:pickle")

        logger.info(f"✓ JSON result: {json_result}")
        logger.info(f"✓ Pickle result: {pickle_result}")
        logger.info("  (Both are equivalent, but stored differently)")

    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")

    print()


def example_5_redis_health_check():
    """Health check and connection verification."""
    logger.info("=" * 70)
    logger.info("Example 2.5: Redis Health Check")
    logger.info("=" * 70)

    try:
        # Get cache with automatic health check
        cache = CacheFactory.get_cache(
            name="health_check_example",
            cache_type=CacheType.REDIS,
            ping_on_init=True,  # Perform health check on init
        )

        logger.info("✓ Redis health check passed!")

        # Store and verify
        cache.set("health:status", "ok")
        status = cache.get("health:status")

        logger.info(f"✓ Cache operational: {status}")

    except Exception as e:
        logger.warning(f"⚠️ Redis health check failed: {e}")
        logger.info("   Ensure Redis is running: docker compose up -d")

    print()


def example_6_redis_batch_operations():
    """Batch operations with Redis."""
    logger.info("=" * 70)
    logger.info("Example 2.6: Redis Batch Operations")
    logger.info("=" * 70)

    try:
        cache = CacheFactory.create_redis_cache()

        # Store batch of values
        batch_data = {
            f"api:endpoint:{i}": {"method": "GET", "path": f"/api/v1/item/{i}"}
            for i in range(5)
        }

        for key, value in batch_data.items():
            cache.set(key, value)

        logger.info(f"✓ Stored {len(batch_data)} API endpoint definitions")

        # Retrieve with pattern
        pattern = "api:endpoint:*"
        keys = cache.keys(pattern)
        logger.info(f"✓ Keys matching '{pattern}': {len(keys)} found")

        # Retrieve values
        for key in keys[:3]:
            value = cache.get(key)
            logger.info(f"  {key}: {value}")

    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 02: Redis Cache")
    logger.info("=" * 70 + "\n")

    try:
        example_1_redis_basic_operations()
        # example_2_redis_with_ttl()
        # example_3_redis_with_key_prefix()
        # example_4_redis_different_serialization()
        # example_5_redis_health_check()
        # example_6_redis_batch_operations()

        logger.info("=" * 70)
        logger.info("✓ All Redis cache examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
