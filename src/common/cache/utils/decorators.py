# common/cache/decorators.py

import asyncio
import functools
import hashlib
import json
from collections.abc import Callable
from typing import Any

from common.cache.cache_factory import CacheFactory, CacheType
from common.cache.cache_interface import CacheInterface
from common.logger import LoggerFactory, LoggerType, LogLevel

# Create logger for cache decorators
logger = LoggerFactory.get_logger(
    name="cache-decorators", logger_type=LoggerType.STANDARD, level=LogLevel.DEBUG
)


def _normalize_cache_type(cache_type: str | CacheType) -> CacheType:
    """
    Convert string cache type to CacheType enum.

    Args:
        cache_type: Either a CacheType enum or string ("memory", "redis", "file")

    Returns:
        CacheType enum

    Raises:
        ValueError: If cache_type is invalid
    """
    if isinstance(cache_type, CacheType):
        return cache_type

    if isinstance(cache_type, str):
        cache_type_lower = cache_type.lower()
        for ct in CacheType:
            if ct.value == cache_type_lower:
                return ct
        raise ValueError(
            f"Invalid cache_type '{cache_type}'. "
            f"Must be one of: {[ct.value for ct in CacheType]}"
        )

    raise TypeError(
        f"cache_type must be string or CacheType enum, got {type(cache_type).__name__}"
    )


def cache_result(
    cache: CacheInterface | None = None,
    ttl: int | None = None,
    key_prefix: str = "",
    include_args: bool = True,
    include_kwargs: bool = True,
    exclude_args: list | None = None,
    exclude_kwargs: list | None = None,
    cache_type: str | CacheType = CacheType.REDIS,
    cache_name: str = "decorator_cache",
    key_fn: Callable[[Callable, tuple, dict], str] | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
    **cache_kwargs,
):
    """
    Decorator to cache function results with TTL support and enhanced logging.
    Supports both sync and async functions.

    Args:
        cache: Pre-configured CacheInterface instance (optional)
        ttl: Time-to-live in seconds for cached values
        key_prefix: Prefix for cache keys
        include_args: Include function args in cache key
        include_kwargs: Include function kwargs in cache key
        exclude_args: List of arg indices to exclude from key
        exclude_kwargs: List of kwarg names to exclude from key
        cache_type: Type of cache ("memory", "redis", "file" or CacheType enum)
        cache_name: Name for the cache instance
        key_fn: Optional custom function to generate cache keys: (func, args, kwargs) -> str
        on_error: Optional error callback: (error_type, exception) -> None
        **cache_kwargs: Additional arguments for cache constructor
    """

    def decorator(func: Callable) -> Callable:
        # Normalize cache_type (convert string to enum)
        try:
            normalized_cache_type = _normalize_cache_type(cache_type)
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid cache_type for {func.__name__}: {e}"
            logger.error(error_msg)
            if on_error:
                on_error("cache_type_error", e)
            raise

        # Get or create cache instance
        if cache is not None:
            cache_instance = cache
            logger.debug(f"Using provided cache instance for {func.__name__}")
        else:
            try:
                cache_instance = CacheFactory.get_cache(
                    name=cache_name, cache_type=normalized_cache_type, **cache_kwargs
                )
                logger.debug(
                    f"Created {normalized_cache_type.value} cache instance for {func.__name__}"
                )
            except Exception as e:
                error_msg = f"Failed to create cache instance for {func.__name__}: {e}"
                logger.error(error_msg)
                if on_error:
                    on_error("cache_creation_error", e)
                # Fallback to memory cache
                try:
                    cache_instance = CacheFactory.get_cache(
                        name=f"{cache_name}_fallback", cache_type=CacheType.MEMORY
                    )
                    logger.warning(f"Using memory cache fallback for {func.__name__}")
                except Exception as fallback_error:
                    error_msg = f"Even fallback cache failed for {func.__name__}: {fallback_error}"
                    logger.error(error_msg)
                    if on_error:
                        on_error("fallback_cache_error", fallback_error)
                    raise

        # Check if function is async
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Generate cache key
                try:
                    if key_fn is not None:
                        # Use custom key function
                        cache_key = key_fn(func, args, kwargs)
                        logger.debug(
                            f"Generated cache key using custom key_fn: {cache_key}"
                        )
                    else:
                        # Use default key generation
                        cache_key = _generate_cache_key(
                            func=func,
                            args=args,
                            kwargs=kwargs,
                            key_prefix=key_prefix,
                            include_args=include_args,
                            include_kwargs=include_kwargs,
                            exclude_args=exclude_args or [],
                            exclude_kwargs=exclude_kwargs or [],
                        )
                        logger.debug(
                            f"Generated cache key for {func.__name__}: {cache_key}"
                        )
                except Exception as e:
                    error_msg = f"Failed to generate cache key for {func.__name__}: {e}"
                    logger.error(error_msg)
                    if on_error:
                        on_error("key_generation_error", e)
                    # Execute function without caching
                    return await func(*args, **kwargs)

                # Try to get from cache
                try:
                    cached_result = cache_instance.get(cache_key)
                    if cached_result is not None:
                        logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                        return cached_result
                    else:
                        logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
                except Exception as e:
                    logger.error(f"Cache get failed for {func.__name__}: {e}")
                    # Continue to execute function

                # Execute function and cache result
                try:
                    result = await func(*args, **kwargs)

                    # Try to cache the result
                    try:
                        cache_success = cache_instance.set(cache_key, result, ttl)
                        if cache_success:
                            logger.debug(
                                f"Cached result for {func.__name__}: {cache_key} (TTL: {ttl})"
                            )
                        else:
                            logger.warning(
                                f"Failed to cache result for {func.__name__}: {cache_key}"
                            )
                    except Exception as cache_error:
                        logger.error(
                            f"Cache set failed for {func.__name__}: {cache_error}"
                        )

                    return result

                except Exception as e:
                    logger.error(f"Function execution failed for {func.__name__}: {e}")
                    raise

            wrapper = async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Generate cache key
                try:
                    if key_fn is not None:
                        # Use custom key function
                        cache_key = key_fn(func, args, kwargs)
                        logger.debug(
                            f"Generated cache key using custom key_fn: {cache_key}"
                        )
                    else:
                        # Use default key generation
                        cache_key = _generate_cache_key(
                            func=func,
                            args=args,
                            kwargs=kwargs,
                            key_prefix=key_prefix,
                            include_args=include_args,
                            include_kwargs=include_kwargs,
                            exclude_args=exclude_args or [],
                            exclude_kwargs=exclude_kwargs or [],
                        )
                        logger.debug(
                            f"Generated cache key for {func.__name__}: {cache_key}"
                        )
                except Exception as e:
                    error_msg = f"Failed to generate cache key for {func.__name__}: {e}"
                    logger.error(error_msg)
                    if on_error:
                        on_error("key_generation_error", e)
                    # Execute function without caching
                    return func(*args, **kwargs)

                # Try to get from cache
                try:
                    cached_result = cache_instance.get(cache_key)
                    if cached_result is not None:
                        logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                        return cached_result
                    else:
                        logger.debug(f"Cache miss for {func.__name__}: {cache_key}")
                except Exception as e:
                    logger.error(f"Cache get failed for {func.__name__}: {e}")
                    # Continue to execute function

                # Execute function and cache result
                try:
                    result = func(*args, **kwargs)

                    # Try to cache the result
                    try:
                        cache_success = cache_instance.set(cache_key, result, ttl)
                        if cache_success:
                            logger.debug(
                                f"Cached result for {func.__name__}: {cache_key} (TTL: {ttl})"
                            )
                        else:
                            logger.warning(
                                f"Failed to cache result for {func.__name__}: {cache_key}"
                            )
                    except Exception as cache_error:
                        logger.error(
                            f"Cache set failed for {func.__name__}: {cache_error}"
                        )

                    return result

                except Exception as e:
                    logger.error(f"Function execution failed for {func.__name__}: {e}")
                    raise

            wrapper = sync_wrapper

        # Add cache management methods to wrapper
        wrapper._cache_instance = cache_instance
        wrapper._cache_key_prefix = key_prefix
        wrapper._original_func = func

        def clear_cache():
            """Clear all cached results for this function"""
            try:
                prefix = f"{key_prefix}{func.__module__}.{func.__name__}"
                keys = cache_instance.keys(f"{prefix}*")
                cleared_count = 0
                for key in keys:
                    if cache_instance.delete(key):
                        cleared_count += 1
                logger.info(
                    f"Cleared {cleared_count} cache entries for {func.__name__}"
                )
            except Exception as e:
                logger.error(f"Failed to clear cache for {func.__name__}: {e}")

        def get_cache_info():
            """Get cache information for this function"""
            try:
                prefix = f"{key_prefix}{func.__module__}.{func.__name__}"
                keys = cache_instance.keys(f"{prefix}*")
                stats = cache_instance.get_stats()
                info = {
                    "cached_entries": len(keys),
                    "cache_keys": keys,
                    "cache_stats": stats,
                    "cache_type": type(cache_instance).__name__,
                }
                logger.debug(
                    f"Cache info for {func.__name__}: {info['cached_entries']} entries"
                )
                return info
            except Exception as e:
                logger.error(f"Failed to get cache info for {func.__name__}: {e}")
                return {"error": str(e)}

        def invalidate_cache(*args, **kwargs):
            """Invalidate cache for specific arguments"""
            try:
                cache_key = _generate_cache_key(
                    func=func,
                    args=args,
                    kwargs=kwargs,
                    key_prefix=key_prefix,
                    include_args=include_args,
                    include_kwargs=include_kwargs,
                    exclude_args=exclude_args or [],
                    exclude_kwargs=exclude_kwargs or [],
                )
                result = cache_instance.delete(cache_key)
                logger.debug(
                    f"Invalidated cache for {func.__name__}: {cache_key} (success: {result})"
                )
                return result
            except Exception as e:
                logger.error(f"Failed to invalidate cache for {func.__name__}: {e}")
                return False

        wrapper.clear_cache = clear_cache
        wrapper.get_cache_info = get_cache_info
        wrapper.invalidate_cache = invalidate_cache

        return wrapper

    return decorator


def _generate_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: str,
    include_args: bool,
    include_kwargs: bool,
    exclude_args: list,
    exclude_kwargs: list,
) -> str:
    """Generate cache key from function and arguments"""

    key_parts = [key_prefix, func.__module__, func.__name__]

    # Include positional arguments
    if include_args and args:
        filtered_args = [arg for i, arg in enumerate(args) if i not in exclude_args]
        if filtered_args:
            # Serialize args safely for key generation
            args_str = _serialize_for_key(filtered_args)
            key_parts.append(f"args:{args_str}")

    # Include keyword arguments
    if include_kwargs and kwargs:
        filtered_kwargs = {k: v for k, v in kwargs.items() if k not in exclude_kwargs}
        if filtered_kwargs:
            # Sort kwargs for consistent key generation
            sorted_kwargs = dict(sorted(filtered_kwargs.items()))
            kwargs_str = _serialize_for_key(sorted_kwargs)
            key_parts.append(f"kwargs:{kwargs_str}")

    # Create final key
    key = "|".join(str(part) for part in key_parts if part)

    # Hash the key if it's too long
    if len(key) > 200:
        key_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
        final_key = f"{key_prefix}hash:{key_hash}"
        logger.debug(f"Generated hashed cache key (original too long): {final_key}")
        return final_key

    return key


def _serialize_for_key(obj: Any) -> str:
    """Serialize object for use in cache key"""
    try:
        # Handle Pydantic models
        if hasattr(obj, "model_dump"):
            return json.dumps(obj.model_dump(), sort_keys=True, default=str)
        # Handle dict-like objects
        elif hasattr(obj, "__dict__"):
            return json.dumps(obj.__dict__, sort_keys=True, default=str)
        # Try JSON serialization first (fastest and most readable)
        return json.dumps(obj, sort_keys=True, default=str)
    except (TypeError, ValueError):
        # Fallback to string representation
        return str(obj)


def cache_property(
    cache: CacheInterface | None = None,
    ttl: int | None = None,
    cache_type: str | CacheType = CacheType.MEMORY,
    cache_name: str = "property_cache",
    on_error: Callable[[str, Exception], None] | None = None,
    **cache_kwargs,
):
    """
    Decorator to cache property results

    Args:
        cache: Cache instance to use
        ttl: Time to live in seconds
        cache_type: Type of cache to create if cache is None ("memory", "redis", "file" or CacheType enum)
        cache_name: Name for the cache instance
        on_error: Optional error callback: (error_type, exception) -> None
        **cache_kwargs: Additional arguments for cache creation

    Returns:
        Decorated property
    """

    def decorator(func: Callable) -> property:
        # Normalize cache_type
        try:
            normalized_cache_type = _normalize_cache_type(cache_type)
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid cache_type for {func.__name__}: {e}"
            logger.error(error_msg)
            if on_error:
                on_error("cache_type_error", e)
            raise

        # Get or create cache instance
        if cache is not None:
            cache_instance = cache
        else:
            try:
                cache_instance = CacheFactory.get_cache(
                    name=cache_name, cache_type=normalized_cache_type, **cache_kwargs
                )
            except Exception as e:
                logger.error(
                    f"Failed to create cache for property {func.__name__}: {e}"
                )
                if on_error:
                    on_error("cache_creation_error", e)
                raise

        @functools.wraps(func)
        def wrapper(self):
            # Generate cache key based on object id and method name
            cache_key = f"property:{id(self)}:{func.__name__}"

            # Try to get from cache
            cached_result = cache_instance.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute property and cache result
            result = func(self)
            cache_instance.set(cache_key, result, ttl)

            return result

        return property(wrapper)

    return decorator


class cached_method:
    """
    Descriptor for caching instance method results
    """

    def __init__(
        self,
        cache: CacheInterface | None = None,
        ttl: int | None = None,
        cache_type: str | CacheType = CacheType.MEMORY,
        cache_name: str = "method_cache",
        include_self: bool = False,
        on_error: Callable[[str, Exception], None] | None = None,
        **cache_kwargs,
    ):
        self.cache = cache
        self.ttl = ttl
        self.cache_type = cache_type
        self.cache_name = cache_name
        self.include_self = include_self
        self.on_error = on_error
        self.cache_kwargs = cache_kwargs
        self.func = None
        self.cache_instance = None

    def __call__(self, func: Callable) -> "cached_method":
        self.func = func
        # Normalize cache_type
        try:
            normalized_cache_type = _normalize_cache_type(self.cache_type)
        except (ValueError, TypeError) as e:
            error_msg = f"Invalid cache_type for {func.__name__}: {e}"
            logger.error(error_msg)
            if self.on_error:
                self.on_error("cache_type_error", e)
            raise

        # Get or create cache instance
        if self.cache is not None:
            self.cache_instance = self.cache
        else:
            try:
                self.cache_instance = CacheFactory.get_cache(
                    name=self.cache_name,
                    cache_type=normalized_cache_type,
                    **self.cache_kwargs,
                )
            except Exception as e:
                logger.error(f"Failed to create cache for method {func.__name__}: {e}")
                if self.on_error:
                    self.on_error("cache_creation_error", e)
                raise
        return self

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        @functools.wraps(self.func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if self.include_self:
                cache_args = (obj,) + args
            else:
                cache_args = args

            cache_key = _generate_cache_key(
                func=self.func,
                args=cache_args,
                kwargs=kwargs,
                key_prefix=f"method:{id(obj)}:",
                include_args=True,
                include_kwargs=True,
                exclude_args=[],
                exclude_kwargs=[],
            )

            # Try to get from cache
            cached_result = self.cache_instance.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute method and cache result
            result = self.func(obj, *args, **kwargs)
            self.cache_instance.set(cache_key, result, self.ttl)

            return result

        return wrapper
