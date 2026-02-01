# common/cache/__init__.py


from common.cache.adapters.file_cache import FileCache
from common.cache.adapters.in_memory_cache import InMemoryCache
from common.cache.adapters.redis_cache import RedisCache
from common.cache.cache_factory import CacheFactory, CacheType
from common.cache.cache_interface import CacheInterface, CacheStats, CacheStatus
from common.cache.utils.decorators import cache_property, cache_result, cached_method

__all__ = [
    "CacheInterface",
    "CacheStatus",
    "CacheStats",
    "InMemoryCache",
    "RedisCache",
    "FileCache",
    "CacheFactory",
    "CacheType",
    "cache_result",
    "cache_property",
    "cached_method",
]
