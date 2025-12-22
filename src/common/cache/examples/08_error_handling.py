"""
Example 08: Error Handling & Resilience
Demonstrates error handling, fallback strategies, and cache resilience.

Topics:
- on_error callback
- Graceful cache failures
- Fallback to memory cache
- Cache health checks
- Error recovery strategies
"""

from common.cache import CacheFactory, CacheType
from common.cache.utils.decorators import cache_result
from common.logger import get_logger

logger = get_logger(__name__)


# Example 1: Custom error handler
error_log = []

def custom_error_handler(error_type: str, exception: Exception):
    """Custom error handler that logs errors."""
    error_msg = f"[{error_type}] {str(exception)}"
    error_log.append(error_msg)
    logger.warning(f"Cache error: {error_msg}")


@cache_result(
    cache_type=CacheType.MEMORY,
    on_error=custom_error_handler,
    ttl=3600,
)
def fetch_data_with_error_handling(data_id: int):
    """Function with custom error handler."""
    logger.info(f"  [Service] Fetching data {data_id}...")
    return {"id": data_id, "status": "ok"}


# Example 2: Fallback cache type
@cache_result(
    cache_type=CacheType.REDIS,  # Will try Redis first
    on_error=lambda et, e: logger.debug(f"Redis failed, using fallback"),
)
def fetch_with_redis_fallback(item_id: str):
    """Will fallback to memory cache if Redis fails."""
    logger.info(f"  [DB] Loading item {item_id}...")
    return {"item_id": item_id, "content": f"Item {item_id}"}


# Example 3: Graceful degradation without cache
def handle_cache_error(error_type: str, exception: Exception):
    """Handle error and optionally degrade gracefully."""
    if error_type == "cache_creation_error":
        logger.warning(f"Cache unavailable: {exception}")
        logger.info("  Continuing without caching...")


@cache_result(
    cache_type=CacheType.REDIS,
    on_error=handle_cache_error,
)
def compute_expensive_operation(complexity: int):
    """Function that can work without cache if needed."""
    logger.info(f"  [Compute] Complex operation (complexity={complexity})...")
    return {"result": complexity ** 2, "computed": True}


def example_1_error_handler_callback():
    """Using on_error callback."""
    logger.info("=" * 70)
    logger.info("Example 8.1: Error Handler Callback")
    logger.info("=" * 70)
    
    # Make calls
    logger.info("▶ Making calls with error handler")
    result1 = fetch_data_with_error_handling(1)
    logger.info(f"✓ Result: {result1}\n")
    
    result2 = fetch_data_with_error_handling(2)
    logger.info(f"✓ Result: {result2}\n")
    
    # Show error log
    if error_log:
        logger.info("✓ Errors caught by handler:")
        for error in error_log:
            logger.info(f"  - {error}")
    else:
        logger.info("✓ No errors caught")
    
    print()


def example_2_fallback_behavior():
    """Fallback to memory cache on error."""
    logger.info("=" * 70)
    logger.info("Example 8.2: Fallback Cache Behavior")
    logger.info("=" * 70)
    
    logger.info("Setup: Trying Redis, with memory fallback")
    logger.info("▶ First call: fetch_with_redis_fallback('item1')")
    
    try:
        result = fetch_with_redis_fallback("item1")
        logger.info(f"✓ Result: {result}\n")
        logger.info("  (Either from Redis or memory fallback)")
    except Exception as e:
        logger.error(f"Failed: {e}\n")
    
    # Second call
    logger.info("▶ Second call (should be cached)")
    result2 = fetch_with_redis_fallback("item1")
    logger.info(f"✓ Result: {result2}\n")
    
    print()


def example_3_graceful_degradation():
    """Graceful degradation without cache."""
    logger.info("=" * 70)
    logger.info("Example 8.3: Graceful Degradation")
    logger.info("=" * 70)
    
    logger.info("Setup: Try Redis, work without cache if it fails")
    logger.info("▶ First call: compute_expensive_operation(10)")
    
    result1 = compute_expensive_operation(10)
    logger.info(f"✓ Result: {result1}")
    logger.info("  Application continues regardless of cache status\n")
    
    logger.info("▶ Second call: compute_expensive_operation(10)")
    result2 = compute_expensive_operation(10)
    logger.info(f"✓ Result: {result2}\n")
    
    print()


def example_4_cache_health_check():
    """Health check before using cache."""
    logger.info("=" * 70)
    logger.info("Example 8.4: Cache Health Check")
    logger.info("=" * 70)
    
    try:
        # Get cache with health check
        logger.info("▶ Creating Redis cache with health check")
        cache = CacheFactory.get_cache(
            name="health_demo",
            cache_type=CacheType.REDIS,
            ping_on_init=True,
        )
        logger.info("✓ Health check passed\n")
        
    except Exception as e:
        logger.warning(f"⚠️ Health check failed: {e}")
        logger.info("✓ Gracefully handled - using memory cache instead\n")
        cache = CacheFactory.get_cache(
            name="health_demo_fallback",
            cache_type=CacheType.MEMORY,
        )
    
    # Use cache
    cache.set("test_key", "test_value")
    value = cache.get("test_key")
    logger.info(f"✓ Cache functional: {value}\n")
    
    print()


def example_5_invalid_cache_type():
    """Handling invalid cache type."""
    logger.info("=" * 70)
    logger.info("Example 8.5: Invalid Cache Type Handling")
    logger.info("=" * 70)
    
    logger.info("Attempting to use invalid cache type:")
    logger.info('▶ @cache_result(cache_type="invalid_type")\n')
    
    try:
        # This will fail gracefully
        @cache_result(cache_type="invalid_type")
        def test_func():
            return "test"
        
        # If we reach here, it was auto-converted or used a fallback
        logger.info("✓ Handled: fell back to default behavior")
        
    except ValueError as e:
        logger.info(f"✓ Caught error: {e}\n")
    except Exception as e:
        logger.error(f"Unexpected error: {e}\n")
    
    print()


def example_6_error_recovery():
    """Error recovery strategies."""
    logger.info("=" * 70)
    logger.info("Example 8.6: Error Recovery Strategies")
    logger.info("=" * 70)
    
    recovery_count = {"cache_creation_error": 0, "key_generation_error": 0}
    
    def recovery_handler(error_type: str, exc: Exception):
        recovery_count[error_type] = recovery_count.get(error_type, 0) + 1
    
    @cache_result(
        cache_type=CacheType.MEMORY,
        on_error=recovery_handler,
    )
    def operation_with_recovery(op_id: int):
        logger.info(f"  [Operation] Executing {op_id}...")
        return {"id": op_id, "status": "completed"}
    
    # Execute operations
    logger.info("▶ Executing operations")
    for i in range(3):
        result = operation_with_recovery(i)
        logger.info(f"  op_{i}: {result}")
    
    logger.info(f"\n✓ Recovery stats: {recovery_count}")
    
    print()


def example_7_best_practices():
    """Best practices for error handling."""
    logger.info("=" * 70)
    logger.info("Example 8.7: Error Handling Best Practices")
    logger.info("=" * 70)
    
    logger.info("✓ DO:")
    logger.info("  • Use on_error callback for monitoring/logging")
    logger.info("  • Fallback to memory cache if primary fails")
    logger.info("  • Perform health checks on startup (ping_on_init=True)")
    logger.info("  • Handle cache failures gracefully (continue without caching)")
    logger.info("  • Log detailed error information for debugging")
    logger.info("  • Monitor error rates and adjust strategy\n")
    
    logger.info("✗ DON'T:")
    logger.info("  • Ignore cache creation errors")
    logger.info("  • Let cache errors propagate to end users")
    logger.info("  • Assume cache always works without verification")
    logger.info("  • Retry aggressively without backoff")
    logger.info("  • Store sensitive data without encryption\n")
    
    logger.info("Error handling pattern:")
    logger.info("  1. Try primary cache (Redis)")
    logger.info("  2. Log error with on_error callback")
    logger.info("  3. Fallback to memory cache automatically")
    logger.info("  4. Continue operation without cache if needed")
    logger.info("  5. Monitor errors and adjust configuration\n")
    
    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 08: Error Handling & Resilience")
    logger.info("=" * 70 + "\n")
    
    try:
        example_1_error_handler_callback()
        example_2_fallback_behavior()
        example_3_graceful_degradation()
        example_4_cache_health_check()
        example_5_invalid_cache_type()
        example_6_error_recovery()
        example_7_best_practices()
        
        logger.info("=" * 70)
        logger.info("✓ All error handling examples completed!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
