"""
Schema-level constraint cache.

Caches constraint extraction results at the schema level to avoid redundant
extraction when multiple operations use the same schema.
"""

from typing import Dict, List, Optional
from common.logger import get_logger

logger = get_logger(__name__)


class SchemaConstraintCache:
    """Cache for schema-level constraint extraction results.

    Caches predicates extracted from schemas to enable reuse when multiple
    operations reference the same schema. Uses schema_name as the cache key.

    Attributes:
        _cache: Dictionary mapping schema names to predicate lists
        _hits: Number of cache hits
        _misses: Number of cache misses

    Example:
        >>> cache = SchemaConstraintCache()
        >>> predicates = cache.get("UserSchema")
        >>> if predicates is None:
        ...     predicates = extract_predicates(schema)
        ...     cache.set("UserSchema", predicates)
    """

    def __init__(self) -> None:
        """Initialize empty cache."""
        self._cache: Dict[str, List[Dict]] = {}
        self._hits: int = 0
        self._misses: int = 0
        logger.debug("Initialized SchemaConstraintCache")

    def get(self, schema_name: str) -> Optional[List[Dict]]:
        """Get cached predicates for a schema.

        Args:
            schema_name: Name of the schema

        Returns:
            List of predicate dictionaries if cached, None otherwise
        """
        if schema_name in self._cache:
            self._hits += 1
            logger.debug(
                "Schema cache HIT",
                schema_name=schema_name,
                predicates_count=len(self._cache[schema_name]),
            )
            return self._cache[schema_name]

        self._misses += 1
        logger.debug("Schema cache MISS", schema_name=schema_name)
        return None

    def set(self, schema_name: str, predicates: List[Dict]) -> None:
        """Cache predicates for a schema.

        Args:
            schema_name: Name of the schema
            predicates: List of predicate dictionaries to cache
        """
        self._cache[schema_name] = predicates
        logger.debug(
            "Schema cache SET",
            schema_name=schema_name,
            predicates_count=len(predicates),
        )

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with hits, misses, and cached_schemas counts
        """
        return {
            "hits": self._hits,
            "misses": self._misses,
            "cached_schemas": len(self._cache),
            "total_requests": self._hits + self._misses,
            "hit_rate": (
                round(self._hits / (self._hits + self._misses), 2)
                if (self._hits + self._misses) > 0
                else 0.0
            ),
        }

    def clear(self) -> None:
        """Clear all cached data and reset statistics."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        logger.debug("Schema cache cleared")
