"""
Example 04: Decorator Basic Usage
Demonstrates @cache_result decorator for caching function results.

Topics:
- Basic decorator usage with different cache types
- TTL configuration
- Key generation
- Argument filtering
- Cache control methods (clear_cache, invalidate_cache, get_cache_info)
"""

from common.cache import CacheType
from common.cache.utils.decorators import cache_result
from common.logger import get_logger

logger = get_logger(__name__)


# Example 1: Basic decorator with memory cache
@cache_result(cache_type=CacheType.MEMORY, ttl=3600)
def fetch_user_data(user_id: int):
    """Simulate fetching user data from database."""
    logger.info(f"  [DB Query] Fetching user {user_id} from database...")
    return {
        "id": user_id,
        "name": f"User_{user_id}",
        "email": f"user{user_id}@example.com",
    }


# Example 2: Decorator with string cache_type (auto-converted to enum)
@cache_result(cache_type="memory", ttl=1800, key_prefix="api:v1:")
def get_product_info(product_id: str):
    """Fetch product information."""
    logger.info(f"  [API Call] Fetching product {product_id}...")
    return {"id": product_id, "name": f"Product {product_id}", "price": 99.99}


# Example 3: Decorator with file cache for persistent caching
@cache_result(cache_type=CacheType.FILE, ttl=86400, cache_dir=".cache/products")
def get_api_spec(api_name: str):
    """Cache OpenAPI specifications."""
    logger.info(f"  [File I/O] Loading OpenAPI spec for {api_name}...")
    return {"api": api_name, "version": "3.0.0", "endpoints": 15}


# Example 4: Decorator excluding arguments from cache key
@cache_result(
    cache_type=CacheType.MEMORY,
    exclude_kwargs=["verbose"],  # Don't include verbose in cache key
)
def calculate_stats(data: list, verbose: bool = False):
    """Calculate statistics (verbose doesn't affect caching)."""
    logger.info(f"  [Calculation] Computing stats for {len(data)} items...")
    return {"count": len(data), "sum": sum(data), "avg": sum(data) / len(data)}


def example_1_basic_decorator():
    """Basic decorator usage."""
    logger.info("=" * 70)
    logger.info("Example 4.1: Basic @cache_result Decorator")
    logger.info("=" * 70)

    # First call - executes function and caches result
    logger.info("▶ First call: fetch_user_data(1)")
    user1 = fetch_user_data(1)
    logger.info(f"✓ Result: {user1}\n")

    # Second call - returns cached result (no DB query)
    logger.info("▶ Second call: fetch_user_data(1) [CACHED]")
    user1_cached = fetch_user_data(1)
    logger.info(f"✓ Result: {user1_cached} (from cache)\n")

    # Different argument - executes function again
    logger.info("▶ Third call: fetch_user_data(2)")
    user2 = fetch_user_data(2)
    logger.info(f"✓ Result: {user2}\n")

    print()


def example_2_string_cache_type():
    """Decorator with string cache type (auto-conversion)."""
    logger.info("=" * 70)
    logger.info("Example 4.2: String Cache Type Auto-Conversion")
    logger.info("=" * 70)

    logger.info("▶ First call: get_product_info('SKU-001')")
    product1 = get_product_info("SKU-001")
    logger.info(f"✓ Result: {product1}\n")

    logger.info("▶ Second call: get_product_info('SKU-001') [CACHED]")
    product1_cached = get_product_info("SKU-001")
    logger.info(f"✓ Result (from cache): {product1_cached}\n")

    logger.info(
        "  Note: cache_type='memory' string was auto-converted to CacheType.MEMORY"
    )

    print()


def example_3_file_cache_decorator():
    """Decorator with file cache for persistence."""
    logger.info("=" * 70)
    logger.info("Example 4.3: Decorator with File Cache")
    logger.info("=" * 70)

    logger.info("▶ First call: get_api_spec('JSONPlaceholder')")
    spec1 = get_api_spec("JSONPlaceholder")
    logger.info(f"✓ Result: {spec1}\n")

    logger.info("▶ Second call: get_api_spec('JSONPlaceholder') [CACHED TO DISK]")
    spec1_cached = get_api_spec("JSONPlaceholder")
    logger.info(f"✓ Result (from disk cache): {spec1_cached}\n")

    logger.info(
        "  Note: Result persisted to .cache/products/ for reuse across restarts"
    )

    print()


def example_4_cache_info_and_control():
    """Cache control methods."""
    logger.info("=" * 70)
    logger.info("Example 4.4: Cache Control Methods")
    logger.info("=" * 70)

    # Make some calls to populate cache
    fetch_user_data(10)
    fetch_user_data(11)
    fetch_user_data(12)

    logger.info("✓ Made 3 cache_result calls")

    # Get cache info
    info = fetch_user_data.get_cache_info()
    logger.info(f"✓ Cache info: {info}")

    print()

    # Invalidate specific cache entry
    logger.info("▶ Invalidating cache for fetch_user_data(10)")
    fetch_user_data.invalidate_cache(10)
    logger.info("✓ Cache entry invalidated\n")

    # Subsequent call will re-execute
    logger.info("▶ Next call to fetch_user_data(10) [RE-EXECUTED]")
    result = fetch_user_data(10)
    logger.info(f"✓ Result: {result}\n")

    print()


def example_5_exclude_arguments():
    """Excluding arguments from cache key."""
    logger.info("=" * 70)
    logger.info("Example 4.5: Excluding Arguments from Cache Key")
    logger.info("=" * 70)

    data = [1, 2, 3, 4, 5]

    # Call with verbose=False
    logger.info("▶ Call: calculate_stats([1,2,3,4,5], verbose=False)")
    result1 = calculate_stats(data, verbose=False)
    logger.info(f"✓ Result: {result1}\n")

    # Same call with verbose=True (same cache key since verbose is excluded)
    logger.info("▶ Call: calculate_stats([1,2,3,4,5], verbose=True) [CACHED]")
    result2 = calculate_stats(data, verbose=True)
    logger.info(f"✓ Result (from cache): {result2}\n")

    logger.info("  Note: 'verbose' argument was excluded from cache key")
    logger.info("         Both calls returned the same cached result")

    print()


def example_6_clear_all_cache():
    """Clear all cached results."""
    logger.info("=" * 70)
    logger.info("Example 4.6: Clear All Cache")
    logger.info("=" * 70)

    # Make calls to populate cache
    fetch_user_data(20)
    fetch_user_data(21)

    info = fetch_user_data.get_cache_info()
    logger.info(f"✓ Cache entries before clear: {info['cached_entries']}")

    # Clear all cache
    logger.info("\n▶ Clearing all cache entries...")
    fetch_user_data.clear_cache()

    info = fetch_user_data.get_cache_info()
    logger.info(f"✓ Cache entries after clear: {info['cached_entries']}\n")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 04: Decorator Basic Usage")
    logger.info("=" * 70 + "\n")

    try:
        example_1_basic_decorator()
        example_2_string_cache_type()
        example_3_file_cache_decorator()
        example_4_cache_info_and_control()
        example_5_exclude_arguments()
        example_6_clear_all_cache()

        logger.info("=" * 70)
        logger.info("✓ All decorator basic examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
