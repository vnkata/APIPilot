"""
Example 01: In-Memory Cache
Demonstrates basic in-memory caching functionality.

Topics:
- Creating and using in-memory cache instances
- Set and get operations
- Cache statistics tracking
- TTL (Time-To-Live) expiration
"""

from common.cache import CacheFactory
from common.logger import get_logger

logger = get_logger(__name__)


def example_1_basic_memory_cache():
    """Create and use a basic in-memory cache."""
    logger.info("=" * 70)
    logger.info("Example 1.1: Basic In-Memory Cache")
    logger.info("=" * 70)

    # Create an in-memory cache using factory
    cache = CacheFactory.create_memory_cache(
        max_size=100,  # Maximum 100 entries
        default_ttl=None,  # No default TTL
        cleanup_interval=60,  # Clean up expired entries every 60 seconds
    )

    logger.info(f"✓ Created memory cache: {type(cache).__name__}")

    # Store values
    cache.set("user:1:name", "Alice")
    cache.set("user:2:name", "Bob")
    cache.set("user:3:name", "Charlie")

    logger.info("✓ Stored 3 values in cache")

    # Retrieve values
    name1 = cache.get("user:1:name")
    name2 = cache.get("user:2:name")

    logger.info(f"✓ Retrieved values: {name1}, {name2}")

    # Check non-existent key
    name_missing = cache.get("user:999:name", default="Unknown")
    logger.info(f"✓ Default value for missing key: {name_missing}")

    # Delete a value
    deleted = cache.delete("user:1:name")
    logger.info(f"✓ Deleted key: {deleted}")

    # Try to get deleted value
    value = cache.get("user:1:name", default="Not found")
    logger.info(f"✓ Value after deletion: {value}")

    print()


def example_2_memory_cache_with_ttl():
    """Demonstrate TTL (Time-To-Live) with memory cache."""
    logger.info("=" * 70)
    logger.info("Example 1.2: Memory Cache with TTL")
    logger.info("=" * 70)

    import time

    cache = CacheFactory.create_memory_cache()

    # Store with 2-second TTL
    cache.set("temp_token", "abc123xyz", ttl=2)
    logger.info("✓ Stored value with 2-second TTL")

    # Retrieve immediately
    value = cache.get("temp_token")
    logger.info(f"✓ Retrieved immediately: {value}")

    # Wait 3 seconds
    logger.info("⏳ Waiting 3 seconds for TTL to expire...")
    time.sleep(3)

    # Try to retrieve expired value
    value = cache.get("temp_token", default="Expired")
    logger.info(f"✓ Retrieved after TTL expired: {value}")

    print()


def example_3_memory_cache_statistics():
    """Track cache statistics and performance."""
    logger.info("=" * 70)
    logger.info("Example 1.3: Cache Statistics")
    logger.info("=" * 70)

    cache = CacheFactory.create_memory_cache()

    # Simulate cache operations
    for i in range(10):
        cache.set(f"key_{i}", f"value_{i}")

    logger.info("✓ Stored 10 values")

    # Perform hits and misses
    for i in range(5):
        cache.get(f"key_{i}")  # HITS

    for i in range(10, 15):
        cache.get(f"key_{i}", default=None)  # MISSES

    # Get statistics
    stats = cache.get_stats()
    logger.info("✓ Cache Stats:")
    logger.info(f"  - Hits: {stats.hits}")
    logger.info(f"  - Misses: {stats.misses}")
    logger.info(f"  - Hit Rate: {stats.get_hit_rate():.2%}")
    logger.info(f"  - Total Operations: {stats.hits + stats.misses}")

    print()


def example_4_memory_cache_size_limit():
    """Demonstrate cache size limits and LRU eviction."""
    logger.info("=" * 70)
    logger.info("Example 1.4: Cache Size Limits & LRU Eviction")
    logger.info("=" * 70)

    # Create cache with 5 entry limit
    cache = CacheFactory.create_memory_cache(
        max_size=5,
        enable_lru=True,  # Enable LRU eviction
    )

    # Add 7 entries (will exceed limit)
    for i in range(7):
        cache.set(f"key_{i}", f"value_{i}")
        keys = cache.keys("*")
        logger.info(f"  Added key_{i}, cache size: {len(keys)}")

    # Check which entries remain (LRU kept most recent)
    remaining_keys = cache.keys("*")
    logger.info(f"✓ Final cache entries (size={len(remaining_keys)}): {remaining_keys}")
    logger.info("  (Oldest entries were evicted due to LRU policy)")

    print()


def example_5_memory_cache_batch_operations():
    """Perform batch operations on cache."""
    logger.info("=" * 70)
    logger.info("Example 1.5: Batch Cache Operations")
    logger.info("=" * 70)

    cache = CacheFactory.create_memory_cache()

    # Set multiple values
    data = {
        "user:1": {"name": "Alice", "age": 30},
        "user:2": {"name": "Bob", "age": 25},
        "user:3": {"name": "Charlie", "age": 35},
    }

    for key, value in data.items():
        cache.set(key, value)

    logger.info(f"✓ Stored {len(data)} complex objects")

    # Get all keys matching pattern
    user_keys = cache.keys("user:*")
    logger.info(f"✓ Keys matching 'user:*': {user_keys}")

    # Retrieve all values
    for key in user_keys:
        value = cache.get(key)
        logger.info(f"  {key}: {value}")

    # Clear all cache
    cache.clear()
    logger.info("✓ Cache cleared")

    remaining = cache.keys("*")
    logger.info(f"✓ Remaining entries: {len(remaining)}")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 01: In-Memory Cache")
    logger.info("=" * 70 + "\n")

    try:
        # example_1_basic_memory_cache()
        # example_2_memory_cache_with_ttl()
        # example_3_memory_cache_statistics()
        # example_4_memory_cache_size_limit()
        # example_5_memory_cache_batch_operations()

        logger.info("=" * 70)
        logger.info("✓ All memory cache examples completed successfully!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
