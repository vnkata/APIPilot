"""
Example 09: Real-World OpenAPI Caching
Demonstrates practical caching of OpenAPI specifications and parsing results.

Topics:
- Caching OpenAPI spec loading and parsing
- File cache for persistent storage
- TTL for API specs
- Cache invalidation strategies
- Multi-level caching (L1: memory, L2: file)
"""

from common.cache import CacheType
from common.cache.utils.decorators import cache_result
from common.logger import get_logger

logger = get_logger(__name__)


# Cache for OpenAPI specs with file persistence
@cache_result(
    cache_type=CacheType.FILE,
    ttl=86400,  # Cache for 24 hours
    cache_dir=".cache/openapi_specs",
    key_prefix="spec:",
)
def load_openapi_spec(spec_name: str) -> dict:
    """Load OpenAPI specification from file."""
    logger.info(f"  [File I/O] Loading OpenAPI spec: {spec_name}")

    # Simulate loading from file
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": spec_name,
            "version": "1.0.0",
            "description": f"OpenAPI spec for {spec_name}",
        },
        "paths": {
            "/users": {
                "get": {"operationId": "getUsers"},
                "post": {"operationId": "createUser"},
            },
            "/users/{id}": {
                "get": {"operationId": "getUserById"},
                "put": {"operationId": "updateUser"},
            },
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                }
            }
        },
    }

    return spec


# Memory cache (L1) for fast access to parsed specs
@cache_result(
    cache_type=CacheType.MEMORY,
    ttl=3600,  # Cache in memory for 1 hour
    key_prefix="parsed:",
)
def parse_openapi_spec(spec_name: str) -> dict:
    """Parse and validate OpenAPI spec."""
    logger.info(f"  [Parsing] Parsing OpenAPI spec: {spec_name}")

    # Load spec (will use cache if available)
    spec = load_openapi_spec(spec_name)

    # Simulate parsing
    paths = spec.get("paths", {})
    endpoints = [
        {"path": path, "methods": list(methods.keys())}
        for path, methods in paths.items()
    ]

    parsed = {
        "title": spec["info"]["title"],
        "version": spec["info"]["version"],
        "endpoints": endpoints,
        "endpoint_count": len(endpoints),
    }

    return parsed


# Generate mock data from OpenAPI spec
def generate_mock_request(spec_name: str, path: str) -> dict:
    """Generate mock request based on OpenAPI spec."""
    logger.info(f"  [Mock] Generating mock request for {path}")
    return {
        "spec": spec_name,
        "path": path,
        "method": "GET",
        "headers": {"Content-Type": "application/json"},
        "body": None,
    }


def example_1_spec_loading():
    """Load and cache OpenAPI specs."""
    logger.info("=" * 70)
    logger.info("Example 9.1: OpenAPI Spec Loading")
    logger.info("=" * 70)

    spec_name = "PetStore"

    # First load - reads from file, caches to disk
    logger.info(f"▶ Loading spec: {spec_name}")
    spec1 = load_openapi_spec(spec_name)
    logger.info(f"✓ Loaded: {spec1['info']['title']} v{spec1['info']['version']}")
    logger.info(f"  Cached to: .cache/openapi_specs/\n")

    # Second load - retrieves from disk cache
    logger.info(f"▶ Loading same spec [FILE CACHE]")
    spec2 = load_openapi_spec(spec_name)
    logger.info(f"✓ Retrieved: {spec2['info']['title']}")
    logger.info(f"  Paths: {list(spec2.get('paths', {}).keys())}\n")

    print()


def example_2_spec_parsing():
    """Parse OpenAPI specs with L1 memory cache."""
    logger.info("=" * 70)
    logger.info("Example 9.2: OpenAPI Spec Parsing with Memory Cache")
    logger.info("=" * 70)

    spec_name = "GitHubAPI"

    # First parse - loads spec (file cache) + parses
    logger.info(f"▶ Parsing spec: {spec_name}")
    parsed1 = parse_openapi_spec(spec_name)
    logger.info(f"✓ Title: {parsed1['title']}")
    logger.info(f"  Endpoints: {parsed1['endpoint_count']}")
    logger.info(f"  Cached in memory for 1 hour\n")

    # Second parse - returns from memory cache
    logger.info(f"▶ Parsing same spec [MEMORY CACHE]")
    parsed2 = parse_openapi_spec(spec_name)
    logger.info(f"✓ Title: {parsed2['title']} (instant)\n")

    print()


def example_3_multi_spec_caching():
    """Cache multiple OpenAPI specs."""
    logger.info("=" * 70)
    logger.info("Example 9.3: Multiple OpenAPI Specs Caching")
    logger.info("=" * 70)

    specs = ["PetStore", "GitHubAPI", "StripeAPI", "SlackAPI"]

    logger.info(f"▶ Loading {len(specs)} OpenAPI specs")

    for spec_name in specs:
        parsed = parse_openapi_spec(spec_name)
        logger.info(f"  ✓ {parsed['title']}: {parsed['endpoint_count']} endpoints")

    logger.info(f"\n✓ All {len(specs)} specs cached (L1: memory, L2: file)\n")

    print()


def example_4_cache_hits_performance():
    """Demonstrate performance improvement from caching."""
    logger.info("=" * 70)
    logger.info("Example 9.4: Cache Hits Performance")
    logger.info("=" * 70)

    import time

    spec_names = ["Spec1", "Spec2", "Spec3"]

    # First round - all cache misses
    logger.info("▶ Round 1: First access (all cache misses)")
    start = time.time()
    for spec in spec_names:
        parse_openapi_spec(spec)
    time1 = time.time() - start
    logger.info(f"  Time: {time1:.3f}s\n")

    # Second round - all cache hits
    logger.info("▶ Round 2: Second access (all cache hits)")
    start = time.time()
    for spec in spec_names:
        parse_openapi_spec(spec)
    time2 = time.time() - start
    logger.info(f"  Time: {time2:.3f}s")
    if time2 > 0:
        logger.info(f"  Speedup: {time1/time2:.1f}x faster with caching\n")
    else:
        logger.info(f"  Speedup: Instant (cached)\n")

    print()


def example_5_cache_organization():
    """Organize cached OpenAPI specs."""
    logger.info("=" * 70)
    logger.info("Example 9.5: Cache Organization Structure")
    logger.info("=" * 70)

    logger.info("File cache directory structure:")
    logger.info("  .cache/openapi_specs/")
    logger.info("  ├── spec:PetStore")
    logger.info("  ├── spec:GitHubAPI")
    logger.info("  ├── spec:StripeAPI")
    logger.info("  └── spec:SlackAPI\n")

    logger.info("Memory cache (L1):")
    logger.info("  parsed:PetStore → fast access")
    logger.info("  parsed:GitHubAPI → fast access")
    logger.info("  parsed:StripeAPI → fast access\n")

    logger.info("Benefits:")
    logger.info("  • L1 (memory): <1ms access time, limited by RAM")
    logger.info("  • L2 (file): 10-100ms, unlimited storage")
    logger.info("  • Two-level reduces parsing overhead dramatically\n")

    print()


def example_6_cache_invalidation():
    """Cache invalidation strategies."""
    logger.info("=" * 70)
    logger.info("Example 9.6: Cache Invalidation Strategies")
    logger.info("=" * 70)

    logger.info("Strategy 1: TIME-BASED (TTL)")
    logger.info("  • File cache: 24 hours (updated specs checked daily)")
    logger.info("  • Memory cache: 1 hour (fresh in-memory copies)")
    logger.info("  • Pro: Automatic, no manual intervention")
    logger.info("  • Con: Delayed invalidation\n")

    logger.info("Strategy 2: EVENT-BASED")
    logger.info("  • On spec update: invalidate cache entry")
    logger.info("  • load_openapi_spec.invalidate_cache('PetStore')")
    logger.info("  • Pro: Immediate consistency")
    logger.info("  • Con: Requires explicit handling\n")

    logger.info("Strategy 3: VERSION-BASED")
    logger.info("  • Key includes version: spec:PetStore:v1.0")
    logger.info("  • New version → new cache entry")
    logger.info("  • Pro: Multiple versions coexist")
    logger.info("  • Con: More complex keys\n")

    logger.info("Strategy 4: CONDITIONAL")
    logger.info("  • Check spec modification time")
    logger.info("  • If newer → reload and re-cache")
    logger.info("  • Pro: Smart invalidation")
    logger.info("  • Con: Extra I/O overhead\n")

    print()


def example_7_real_world_workflow():
    """Real-world OpenAPI caching workflow."""
    logger.info("=" * 70)
    logger.info("Example 9.7: Real-World Workflow")
    logger.info("=" * 70)

    logger.info("Typical workflow:")
    logger.info("")
    logger.info("1. USER REQUEST: Generate test for 'PetStore' API")
    logger.info("   ├─ Check L1 memory cache → MISS")
    logger.info("   └─ Check L2 file cache → MISS (first time)")
    logger.info("")

    parsed = parse_openapi_spec("PetStore")
    logger.info(f"2. CACHE MISS → Load & Parse")
    logger.info(f"   ├─ Load from file (or remote)")
    logger.info(f"   ├─ Parse specification")
    logger.info(f"   └─ Store in L1 (memory) and L2 (file)")
    logger.info("")

    logger.info("3. GENERATE TESTS")
    logger.info(f"   ├─ Read from L1 cache (instant)")
    logger.info(f"   ├─ Generate mock requests")
    logger.info(f"   └─ Generate test cases")
    logger.info("")

    logger.info("4. SUBSEQUENT REQUESTS: Same API")
    logger.info(f"   ├─ Check L1 memory cache → HIT")
    logger.info(f"   └─ Instant access to parsed spec")
    logger.info("")

    logger.info("5. AFTER 1 HOUR")
    logger.info(f"   ├─ L1 memory TTL expires")
    logger.info(f"   ├─ Reload from L2 file cache (fast)")
    logger.info(f"   └─ Store in L1 again")
    logger.info("")

    logger.info("6. AFTER 24 HOURS")
    logger.info(f"   ├─ L2 file TTL expires")
    logger.info(f"   ├─ Reload from original source")
    logger.info(f"   └─ Get latest changes\n")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 09: Real-World OpenAPI Caching")
    logger.info("=" * 70 + "\n")

    try:
        example_1_spec_loading()
        example_2_spec_parsing()
        example_3_multi_spec_caching()
        example_4_cache_hits_performance()
        example_5_cache_organization()
        example_6_cache_invalidation()
        example_7_real_world_workflow()

        logger.info("=" * 70)
        logger.info("✓ All OpenAPI caching examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
