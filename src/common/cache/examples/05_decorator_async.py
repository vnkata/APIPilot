"""
Example 05: Async Decorator Usage
Demonstrates @cache_result decorator with async functions.

Topics:
- Caching async function results
- async/await support
- Concurrent cache operations
- Async + Redis caching
"""

import asyncio

from common.cache import CacheType
from common.cache.utils.decorators import cache_result
from common.logger import get_logger

logger = get_logger(__name__)


# Async function with memory cache
@cache_result(cache_type=CacheType.MEMORY, ttl=3600)
async def fetch_user_async(user_id: int):
    """Async function to fetch user data (simulated API call)."""
    logger.info(f"  [Async API] Fetching user {user_id}...")
    await asyncio.sleep(0.5)  # Simulate async I/O
    return {"id": user_id, "name": f"User_{user_id}", "status": "active"}


# Async function with file cache
@cache_result(cache_type=CacheType.FILE, ttl=86400, cache_dir=".cache/async_results")
async def fetch_weather_data(city: str):
    """Async function to fetch weather data."""
    logger.info(f"  [Async Weather API] Fetching weather for {city}...")
    await asyncio.sleep(0.3)  # Simulate async I/O
    return {"city": city, "temp": 25, "condition": "Sunny"}


# Async function with custom error handling
@cache_result(
    cache_type=CacheType.MEMORY,
    on_error=lambda error_type, exc: logger.warning(
        f"Cache error: {error_type} - {exc}"
    ),
)
async def process_data_async(data_id: int):
    """Async function with error handling."""
    logger.info(f"  [Async Processing] Processing data {data_id}...")
    await asyncio.sleep(0.2)
    return {"data_id": data_id, "processed": True, "result": data_id * 10}


async def example_1_basic_async_cache():
    """Basic async function caching."""
    logger.info("=" * 70)
    logger.info("Example 5.1: Basic Async Cache")
    logger.info("=" * 70)

    # First call - executes async function
    logger.info("▶ First call: fetch_user_async(1)")
    start = asyncio.get_event_loop().time()
    user1 = await fetch_user_async(1)
    elapsed = asyncio.get_event_loop().time() - start
    logger.info(f"✓ Result: {user1}")
    logger.info(f"  Time: {elapsed:.2f}s (async I/O)\n")

    # Second call - returns cached result (instant)
    logger.info("▶ Second call: fetch_user_async(1) [CACHED]")
    start = asyncio.get_event_loop().time()
    user1_cached = await fetch_user_async(1)
    elapsed = asyncio.get_event_loop().time() - start
    logger.info(f"✓ Result: {user1_cached}")
    logger.info(f"  Time: {elapsed:.4f}s (from cache)\n")

    print()


async def example_2_concurrent_async_calls():
    """Concurrent async calls with caching."""
    logger.info("=" * 70)
    logger.info("Example 5.2: Concurrent Async Calls")
    logger.info("=" * 70)

    # First batch - all miss cache, run concurrently
    logger.info("▶ First batch: Fetching users 1-3 concurrently")
    start = asyncio.get_event_loop().time()
    results1 = await asyncio.gather(
        fetch_user_async(1),
        fetch_user_async(2),
        fetch_user_async(3),
    )
    elapsed = asyncio.get_event_loop().time() - start
    logger.info(f"✓ Got {len(results1)} results in {elapsed:.2f}s\n")

    # Second batch - all hit cache, instant
    logger.info("▶ Second batch: Fetching users 1-3 again [ALL CACHED]")
    start = asyncio.get_event_loop().time()
    results2 = await asyncio.gather(
        fetch_user_async(1),
        fetch_user_async(2),
        fetch_user_async(3),
    )
    elapsed = asyncio.get_event_loop().time() - start
    logger.info(f"✓ Got {len(results2)} cached results in {elapsed:.4f}s\n")

    print()


async def example_3_mixed_cached_uncached():
    """Mix of cached and uncached calls."""
    logger.info("=" * 70)
    logger.info("Example 5.3: Mixed Cached and Uncached Calls")
    logger.info("=" * 70)

    # Make some initial calls
    await fetch_weather_data("New York")
    await fetch_weather_data("London")

    logger.info("✓ Initial weather data cached\n")

    # Mix of cached and new calls
    logger.info("▶ Batch: NY (cached), LA (new), London (cached)")
    start = asyncio.get_event_loop().time()
    results = await asyncio.gather(
        fetch_weather_data("New York"),  # Cached
        fetch_weather_data("Los Angeles"),  # New
        fetch_weather_data("London"),  # Cached
    )
    elapsed = asyncio.get_event_loop().time() - start

    logger.info(f"✓ Results: {results}")
    logger.info(f"  Time: {elapsed:.2f}s (faster due to cached entries)\n")

    print()


async def example_4_async_with_error_handling():
    """Async with error handling callback."""
    logger.info("=" * 70)
    logger.info("Example 5.4: Async with Error Handling")
    logger.info("=" * 70)

    try:
        # Normal operation
        logger.info("▶ Processing data 42")
        result1 = await process_data_async(42)
        logger.info(f"✓ Result: {result1}\n")

        # Cached result
        logger.info("▶ Processing data 42 again [CACHED]")
        result2 = await process_data_async(42)
        logger.info(f"✓ Result: {result2}\n")

    except Exception as e:
        logger.error(f"Error: {e}")

    print()


async def example_5_performance_comparison():
    """Compare performance: cached vs uncached."""
    logger.info("=" * 70)
    logger.info("Example 5.5: Performance Comparison")
    logger.info("=" * 70)

    # Uncached function for comparison
    async def fetch_user_uncached(user_id: int):
        logger.info(f"  [Uncached] Fetching user {user_id}...")
        await asyncio.sleep(0.5)
        return {"id": user_id, "name": f"User_{user_id}"}

    # Test uncached
    logger.info("▶ Uncached - 5 sequential calls")
    start = asyncio.get_event_loop().time()
    for i in range(1, 6):
        await fetch_user_uncached(i)
    uncached_time = asyncio.get_event_loop().time() - start
    logger.info(f"  Time: {uncached_time:.2f}s\n")

    # Test cached (first call misses)
    logger.info("▶ Cached - 5 calls (first misses, rest hit)")

    @cache_result(cache_type=CacheType.MEMORY)
    async def fetch_user_cached(user_id: int):
        logger.info(f"  [Cached] Fetching user {user_id}...")
        await asyncio.sleep(0.5)
        return {"id": user_id, "name": f"User_{user_id}"}

    start = asyncio.get_event_loop().time()
    for i in range(1, 6):
        await fetch_user_cached(i)
    cached_time = asyncio.get_event_loop().time() - start
    logger.info(f"  Time: {cached_time:.2f}s\n")

    logger.info(f"✓ Speedup: {uncached_time / cached_time:.1f}x faster with caching")

    print()


async def main():
    """Run all async examples."""
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 05: Async Decorator")
    logger.info("=" * 70 + "\n")

    try:
        await example_1_basic_async_cache()
        await example_2_concurrent_async_calls()
        await example_3_mixed_cached_uncached()
        await example_4_async_with_error_handling()
        await example_5_performance_comparison()

        logger.info("=" * 70)
        logger.info("✓ All async decorator examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
