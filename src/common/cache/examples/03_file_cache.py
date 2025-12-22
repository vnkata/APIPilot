"""
Example 03: File Cache
Demonstrates persistent caching to disk using FileCache.

Topics:
- Persistent disk-based caching
- Cache directory management
- Safe filenames and subdirectories
- Serialization to disk
- File cleanup and lifecycle management
"""

from common.cache import CacheFactory
from common.logger import get_logger

logger = get_logger(__name__)


def example_1_basic_file_cache():
    """Create and use file cache."""
    logger.info("=" * 70)
    logger.info("Example 3.1: Basic File Cache")
    logger.info("=" * 70)

    cache = CacheFactory.create_file_cache(
        cache_dir=".cache/demo",
        serialization="json",
        create_subdirs=True,
        safe_filenames=True,
    )

    logger.info(f"✓ Created file cache: {type(cache).__name__}")
    logger.info(f"  Cache directory: .cache/demo")

    # Store values to disk
    cache.set("user:1:data", {"name": "Alice", "role": "admin"})
    cache.set("user:2:data", {"name": "Bob", "role": "user"})

    logger.info("✓ Stored 2 values to disk")

    # Retrieve from disk
    user1 = cache.get("user:1:data")
    logger.info(f"✓ Retrieved from disk: {user1}")

    # Check keys
    keys = cache.keys("*")
    logger.info(f"✓ Cache keys: {keys}")

    print()


def example_2_file_cache_persistence():
    """Demonstrate persistence across sessions."""
    logger.info("=" * 70)
    logger.info("Example 3.2: File Cache Persistence")
    logger.info("=" * 70)

    import time

    cache = CacheFactory.create_file_cache(cache_dir=".cache/demo")

    # Store persistent data
    cache.set("persistent:config", {"app_name": "Demo", "version": "1.0.0"})
    logger.info("✓ Stored persistent configuration")

    # Verify immediately
    config = cache.get("persistent:config")
    logger.info(f"✓ Retrieved immediately: {config}")

    # In a real scenario, this data would persist across restarts
    logger.info("⏳ Data persisted to disk at .cache/demo/")
    logger.info("  (Would be available after process restart)")

    print()


def example_3_file_cache_with_ttl():
    """File cache with TTL support."""
    logger.info("=" * 70)
    logger.info("Example 3.3: File Cache with TTL")
    logger.info("=" * 70)

    import time

    cache = CacheFactory.create_file_cache(cache_dir=".cache/demo")

    # Store with 2-second TTL
    cache.set("temp:session", "session_id_123", ttl=2)
    logger.info("✓ Stored temporary session with 2-second TTL")

    # Retrieve immediately
    session = cache.get("temp:session")
    logger.info(f"✓ Retrieved immediately: {session}")

    # Wait for expiration
    logger.info("⏳ Waiting 3 seconds for TTL to expire...")
    time.sleep(3)

    # Try to retrieve expired value
    session = cache.get("temp:session", default="Expired")
    logger.info(f"✓ After TTL expired: {session}")

    print()


def example_4_file_cache_organization():
    """Using subdirectories for organization."""
    logger.info("=" * 70)
    logger.info("Example 3.4: File Cache Organization")
    logger.info("=" * 70)

    cache = CacheFactory.create_file_cache(
        cache_dir=".cache/organized",
        create_subdirs=True,  # Auto-create subdirs
        safe_filenames=True,
    )

    # Store organized data
    cache.set("users/alice/profile", {"name": "Alice", "email": "alice@example.com"})
    cache.set("users/bob/profile", {"name": "Bob", "email": "bob@example.com"})
    cache.set("config/app/settings", {"debug": True, "timeout": 30})

    logger.info("✓ Stored data with organized key hierarchy")
    logger.info("  Files created in subdirectories:")

    # Show structure
    all_keys = cache.keys("*")
    logger.info(f"  Keys: {all_keys}")

    print()


def example_5_file_cache_cleanup():
    """File cache cleanup and maintenance."""
    logger.info("=" * 70)
    logger.info("Example 3.5: File Cache Cleanup")
    logger.info("=" * 70)

    cache = CacheFactory.create_file_cache(
        cache_dir=".cache/cleanup",
        cleanup_interval=60,  # Auto-cleanup every 60 seconds
    )

    # Store multiple entries
    for i in range(10):
        cache.set(f"entry_{i}", f"value_{i}")

    logger.info("✓ Stored 10 cache entries")

    # Get statistics
    keys_before = cache.keys("*")
    logger.info(f"✓ Keys before cleanup: {len(keys_before)}")

    # Delete some entries
    for i in range(5):
        cache.delete(f"entry_{i}")

    keys_after = cache.keys("*")
    logger.info(f"✓ Keys after cleanup: {len(keys_after)}")

    # Clear all
    cache.clear()
    logger.info("✓ Cache cleared completely")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 03: File Cache")
    logger.info("=" * 70 + "\n")

    try:
        example_1_basic_file_cache()
        example_2_file_cache_persistence()
        example_3_file_cache_with_ttl()
        example_4_file_cache_organization()
        example_5_file_cache_cleanup()

        logger.info("=" * 70)
        logger.info("✓ All file cache examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
