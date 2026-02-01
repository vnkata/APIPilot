"""
Example 07: TTL Lifecycle Management
Demonstrates Time-To-Live (TTL) expiration and cache lifecycle.

Topics:
- TTL configuration (per-entry and default)
- TTL expiration behavior
- Cache refresh strategies
- TTL monitoring
"""

import time

from common.cache import CacheFactory, CacheType
from common.cache.utils.decorators import cache_result
from common.logger import get_logger

logger = get_logger(__name__)


@cache_result(cache_type=CacheType.MEMORY, ttl=2)  # 2-second TTL
def fetch_volatile_data(request_id: int):
    """Function with short TTL for volatile data."""
    logger.info(f"  [API] Fetching volatile data {request_id}...")
    return {
        "request_id": request_id,
        "data": f"data_{request_id}",
        "timestamp": time.time(),
    }


@cache_result(cache_type=CacheType.MEMORY, ttl=86400)  # 24-hour TTL
def fetch_stable_config(config_name: str):
    """Function with long TTL for stable configuration."""
    logger.info(f"  [Config] Loading {config_name}...")
    return {"name": config_name, "version": "1.0", "loaded_at": time.time()}


def example_1_ttl_expiration():
    """Demonstrate TTL expiration."""
    logger.info("=" * 70)
    logger.info("Example 7.1: TTL Expiration")
    logger.info("=" * 70)

    # Store with 2-second TTL
    logger.info("▶ Storing data with 2-second TTL")
    result1 = fetch_volatile_data(1)
    logger.info(f"✓ Stored: {result1}\n")

    # Immediately retrieve (cache hit)
    logger.info("▶ Retrieving after 0.5 seconds [CACHE HIT]")
    time.sleep(0.5)
    result2 = fetch_volatile_data(1)
    logger.info(f"✓ Result: {result2}")
    logger.info("  Same timestamp = same cached result\n")

    # Wait for expiration
    logger.info("▶ Waiting 2.5 seconds for TTL to expire...")
    time.sleep(2.5)

    # Retrieve after expiration (cache miss)
    logger.info("✓ Retrieving after TTL expired [CACHE MISS]")
    result3 = fetch_volatile_data(1)
    logger.info(f"✓ Result: {result3}")
    logger.info("  Different timestamp = fresh computation\n")

    print()


def example_2_different_ttl_values():
    """Compare different TTL configurations."""
    logger.info("=" * 70)
    logger.info("Example 7.2: Different TTL Values")
    logger.info("=" * 70)

    cache_short = CacheFactory.create_memory_cache()
    cache_long = CacheFactory.create_memory_cache()

    # Store with different TTLs
    logger.info("▶ Storing same data with different TTLs")
    cache_short.set("data", "value", ttl=1)
    cache_long.set("data", "value", ttl=10)
    logger.info("  cache_short: 1-second TTL")
    logger.info("  cache_long: 10-second TTL\n")

    # Check after 2 seconds
    logger.info("▶ After 2 seconds:")
    time.sleep(2)

    short_val = cache_short.get("data")
    long_val = cache_long.get("data")

    logger.info(f"  cache_short: {short_val} (expired)")
    logger.info(f"  cache_long: {long_val} (still valid)\n")

    print()


def example_3_no_ttl_permanent():
    """Cache entries without TTL (permanent)."""
    logger.info("=" * 70)
    logger.info("Example 7.3: Permanent Cache (No TTL)")
    logger.info("=" * 70)

    cache = CacheFactory.create_memory_cache()

    # Store without TTL
    logger.info("▶ Storing config data without TTL")
    cache.set("config:app:version", "2.1.0", ttl=None)
    logger.info("  TTL=None: data persists until manually deleted\n")

    # Verify persistence
    logger.info("▶ After 5 seconds:")
    time.sleep(5)
    value = cache.get("config:app:version")
    logger.info(f"✓ Value still exists: {value}\n")

    # Only manual delete removes it
    logger.info("▶ Manually deleting...")
    cache.delete("config:app:version")
    value = cache.get("config:app:version")
    logger.info(f"✓ After delete: {value}\n")

    print()


def example_4_ttl_monitoring():
    """Monitor TTL and expiration."""
    logger.info("=" * 70)
    logger.info("Example 7.4: TTL Monitoring")
    logger.info("=" * 70)

    cache = CacheFactory.create_memory_cache()

    # Store with TTL
    logger.info("▶ Storing with 5-second TTL")
    cache.set("monitor:key", "test_value", ttl=5)
    logger.info("✓ Stored\n")

    # Check at different intervals
    for i in range(7):
        time.sleep(1)
        value = cache.get("monitor:key")
        status = "✓ Valid" if value else "✗ Expired"
        logger.info(f"  After {i + 1}s: {status}")

    print()


def example_5_ttl_with_decorator():
    """TTL behavior with decorators."""
    logger.info("=" * 70)
    logger.info("Example 7.5: TTL with @cache_result Decorator")
    logger.info("=" * 70)

    logger.info("▶ Function: fetch_volatile_data() with ttl=2")
    logger.info("")

    # Calls with timing
    logger.info("Call 1 (t=0s): execute function")
    time.sleep(0.1)
    result1 = fetch_volatile_data(100)
    timestamp1 = result1["timestamp"]
    logger.info(f"✓ Result: {result1}\n")

    logger.info("Call 2 (t=0.5s): return from cache")
    time.sleep(0.4)
    result2 = fetch_volatile_data(100)
    timestamp2 = result2["timestamp"]
    logger.info(f"✓ Result: {result2}")
    logger.info(f"  Same timestamp: {timestamp1 == timestamp2}\n")

    logger.info("Call 3 (t=3s): cache expired, re-execute")
    time.sleep(2.5)
    result3 = fetch_volatile_data(100)
    timestamp3 = result3["timestamp"]
    logger.info(f"✓ Result: {result3}")
    logger.info(f"  Different timestamp: {timestamp3 > timestamp2}\n")

    print()


def example_6_ttl_strategy():
    """Different TTL strategies."""
    logger.info("=" * 70)
    logger.info("Example 7.6: TTL Strategies")
    logger.info("=" * 70)

    logger.info("1. SHORT TTL (seconds): Volatile data")
    logger.info("   Example: Session tokens, real-time metrics")
    logger.info("   Benefit: Always fresh data")
    logger.info("   Cost: More cache misses, more computation\n")

    logger.info("2. MEDIUM TTL (minutes): Semi-stable data")
    logger.info("   Example: User profiles, product info")
    logger.info("   Benefit: Balance between freshness and cache hits")
    logger.info("   Cost: Slightly stale data possible\n")

    logger.info("3. LONG TTL (hours/days): Stable data")
    logger.info("   Example: Configuration, static content")
    logger.info("   Benefit: High cache hit rate, minimal computation")
    logger.info("   Cost: Requires manual invalidation when changed\n")

    logger.info("4. NO TTL (permanent): Static/reference data")
    logger.info("   Example: Lookup tables, enumerations")
    logger.info("   Benefit: Maximum performance, minimal overhead")
    logger.info("   Cost: Must be manually cleared\n")

    print()


def example_7_ttl_best_practices():
    """Best practices for TTL configuration."""
    logger.info("=" * 70)
    logger.info("Example 7.7: TTL Best Practices")
    logger.info("=" * 70)

    logger.info("✓ DO:")
    logger.info("  • Match TTL to data freshness requirements")
    logger.info("  • Use shorter TTL for volatile/user-specific data")
    logger.info("  • Use longer TTL for stable/shared data")
    logger.info("  • Monitor cache hit rates and adjust TTL accordingly")
    logger.info("  • Document TTL decisions in code comments\n")

    logger.info("✗ DON'T:")
    logger.info("  • Set TTL too short (defeats caching purpose)")
    logger.info("  • Set TTL too long (stale data issues)")
    logger.info("  • Use one TTL for all data types")
    logger.info("  • Forget to update TTL when requirements change")
    logger.info("  • Ignore cache expiration behavior in tests\n")

    logger.info("Recommended TTL values:")
    logger.info("  • Real-time data: 1-5 seconds")
    logger.info("  • User sessions: 30 minutes - 2 hours")
    logger.info("  • API responses: 5-15 minutes")
    logger.info("  • Configuration: 1-6 hours")
    logger.info("  • Static content: 1-7 days")
    logger.info("  • Reference data: No TTL (permanent)\n")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 07: TTL Lifecycle Management")
    logger.info("=" * 70 + "\n")

    try:
        example_1_ttl_expiration()
        example_2_different_ttl_values()
        example_3_no_ttl_permanent()
        example_4_ttl_monitoring()
        example_5_ttl_with_decorator()
        example_6_ttl_strategy()
        example_7_ttl_best_practices()

        logger.info("=" * 70)
        logger.info("✓ All TTL lifecycle examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
