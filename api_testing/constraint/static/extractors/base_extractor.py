"""Abstract base class for static constraint extractors.

Provides shared functionality for batching, caching, and error handling
across different types of static constraint extraction.
"""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar

from pydantic import BaseModel

from api_testing.constraint.static.extractors.models import (
    CacheMetadata,
    ExtractionResult,
)
from common.logger import Logger, LogLevel

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput", bound=BaseModel)


def handle_extraction_error(
    return_value: Any = None,
) -> Callable:
    """Decorator for graceful error handling in extraction methods.

    Catches LLMError, AttributeError, and general exceptions, logs them,
    and returns specified return_value instead of raising.

    Args:
        return_value: Value to return on exception (default: None)

    Example:
        >>> @handle_extraction_error(return_value=("item_id", None))
        ... async def extract_item(self, item_id):
        ...     # Extraction logic that may fail
        ...     return item_id, result
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            from common.llm.exceptions import LLMError

            try:
                return await func(self, *args, **kwargs)
            except LLMError as e:
                self.logger.error(
                    f"LLM error in {func.__name__}: {str(e)}",
                    error_type=type(e).__name__,
                )
                return return_value
            except AttributeError as e:
                self.logger.error(
                    f"AttributeError in {func.__name__}: {str(e)}. "
                    f"This may indicate missing schema/parameter fields. "
                    f"Check OpenAPI spec validity.",
                    exc_info=True,
                )
                return return_value
            except Exception as e:
                self.logger.error(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                return return_value

        return wrapper

    return decorator


class BaseStaticExtractor[TInput, TOutput: BaseModel](ABC):
    """Abstract base class for static constraint extractors.

    Provides shared functionality for batch processing, caching, and error handling.
    Subclasses must implement _extract_single() and cache_file property.

    Type Parameters:
        TInput: Input type for single extraction (e.g., Tuple[str, ItemProperties])
        TOutput: Output Pydantic model type (e.g., SchemaConstraints)

    Attributes:
        cache_dir: Directory for cache files
        batch_size: Number of items to process in parallel
        logger: Logger instance for this extractor
    """

    def __init__(
        self,
        cache_dir: str,
        batch_size: int = 10,
        logger: Logger | None = None,
    ) -> None:
        """Initialize base extractor.

        Args:
            cache_dir: Directory path for caching extracted constraints
            batch_size: Number of items to process in parallel (default: 10)
            logger: Logger instance (will create new one if not provided)

        Raises:
            ValueError: If cache_dir is None or batch_size < 1
        """
        if cache_dir is None:
            raise ValueError("cache_dir is required")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        self.cache_dir = cache_dir
        self.batch_size = batch_size

        # Use provided logger or create new one
        if logger is None:
            from common.logger import get_logger

            self.logger = get_logger(
                self.__class__.__name__,
                level=LogLevel.DEBUG,
                console_level=LogLevel.DEBUG,
            )
        else:
            self.logger = logger

    @property
    @abstractmethod
    def cache_file(self) -> str:
        """Path to cache file for this extractor.

        Must be implemented by subclasses to specify cache location.

        Returns:
            Absolute path to cache file
        """
        pass

    @abstractmethod
    async def _extract_single(self, item: TInput) -> tuple[str, TOutput | None]:
        """Extract constraints for a single item.

        Must be implemented by subclasses with specific extraction logic.

        Args:
            item: Input item to extract constraints from

        Returns:
            Tuple of (item_identifier, extracted_constraints)
            Returns None as second element if extraction failed

        Note:
            Should use @handle_extraction_error decorator for error handling
        """
        pass

    async def _extract_batch(
        self, items_batch: list[TInput]
    ) -> ExtractionResult[TOutput]:
        """Extract constraints for a batch of items in parallel.

        Args:
            items_batch: List of items to process

        Returns:
            ExtractionResult with successful/failed items and statistics
        """
        if not items_batch:
            return ExtractionResult[TOutput](
                successful=[],
                failed=[],
                total_processed=0,
            )

        self.logger.debug(f"Processing batch of {len(items_batch)} items")

        # Create tasks for parallel execution
        tasks = [self._extract_single(item) for item in items_batch]

        # Execute all tasks with exception handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful: list[TOutput] = []
        failed: list[tuple[str, str]] = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Exception escaped from decorator - should not happen normally
                item_id = str(i)  # Fallback identifier
                error_msg = f"{type(result).__name__}: {str(result)}"
                self.logger.error(f"Unhandled exception in batch: {error_msg}")
                failed.append((item_id, error_msg))
                continue

            item_id, constraints = result
            if constraints is not None:
                successful.append(constraints)
                self.logger.debug(
                    f"Successfully extracted: {item_id}",
                    constraint_count=len(getattr(constraints, "constraints", {})),
                )
            else:
                failed.append((item_id, "Extraction returned None"))
                self.logger.warning(f"Extraction failed: {item_id}")

        extraction_result = ExtractionResult[TOutput](
            successful=successful,
            failed=failed,
            total_processed=len(items_batch),
        )

        self.logger.debug(
            f"Batch completed: {extraction_result.success_count}/{extraction_result.total_processed} "
            f"successful ({extraction_result.success_rate:.1%})"
        )

        return extraction_result

    async def extract_all(
        self,
        items: list[TInput],
        force_refresh: bool = False,
        item_identifier: Callable[[TInput], str] | None = None,
    ) -> ExtractionResult[TOutput]:
        """Extract constraints for all items with batching and caching.

        Args:
            items: List of items to extract constraints from
            force_refresh: If True, ignore cache and re-extract
            item_identifier: Optional function to get item identifier for logging

        Returns:
            ExtractionResult with all successful/failed extractions
        """
        # Load from cache if exists and not forcing refresh
        if not force_refresh:
            cached_result = self._load_cache()
            if cached_result is not None:
                self.logger.info(
                    f"Loaded {len(cached_result.successful)} items from cache: {self.cache_file}"
                )
                return cached_result

        self.logger.info(f"Processing {len(items)} items for constraint extraction")

        # Process items in batches
        all_successful: list[TOutput] = []
        all_failed: list[tuple[str, str]] = []
        total_processed = 0

        for batch_start in range(0, len(items), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(items))
            batch = items[batch_start:batch_end]
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (len(items) + self.batch_size - 1) // self.batch_size

            # Log batch identifiers if function provided
            if item_identifier:
                batch_ids = [item_identifier(item) for item in batch]
                self.logger.info(
                    f"Processing batch {batch_num}/{total_batches} "
                    f"({batch_start + 1}-{batch_end} of {len(items)}): {batch_ids}"
                )
            else:
                self.logger.info(
                    f"Processing batch {batch_num}/{total_batches} "
                    f"({batch_start + 1}-{batch_end} of {len(items)})"
                )

            batch_result = await self._extract_batch(batch)

            all_successful.extend(batch_result.successful)
            all_failed.extend(batch_result.failed)
            total_processed += batch_result.total_processed

            self.logger.info(
                f"Batch {batch_num}/{total_batches} completed: "
                f"{batch_result.success_count} successful, "
                f"{batch_result.failure_count} failed"
            )

        final_result = ExtractionResult[TOutput](
            successful=all_successful,
            failed=all_failed,
            total_processed=total_processed,
        )

        self.logger.info(
            f"Extraction completed: {final_result.success_count}/{final_result.total_processed} "
            f"successful ({final_result.success_rate:.1%})"
        )

        # Save to cache
        self._save_cache(final_result)

        return final_result

    def _load_cache(self) -> ExtractionResult[TOutput] | None:
        """Load cached extraction results.

        Returns:
            ExtractionResult if cache exists and valid, None otherwise
        """
        if not os.path.exists(self.cache_file):
            return None

        try:
            with open(self.cache_file, encoding="utf-8") as file:
                cached_data = json.load(file)

            # Reconstruct ExtractionResult from cache
            # Cache format: {"metadata": {...}, "data": [...]}
            if "data" not in cached_data:
                self.logger.warning(f"Invalid cache format: {self.cache_file}")
                return None

            # Parse successful items using output model type
            successful = self._parse_cached_items(cached_data["data"])

            result = ExtractionResult[TOutput](
                successful=successful,
                failed=[],  # Don't cache failures
                total_processed=len(successful),
            )

            return result

        except (OSError, json.JSONDecodeError, KeyError) as e:
            self.logger.warning(
                f"Failed to load cache: {self.cache_file}, error={str(e)}"
            )
            return None

    @abstractmethod
    def _parse_cached_items(self, cached_data: list[dict]) -> list[TOutput]:
        """Parse cached items into output model instances.

        Must be implemented by subclasses to reconstruct their specific output type.

        Args:
            cached_data: List of cached item dictionaries

        Returns:
            List of parsed output model instances
        """
        pass

    def _save_cache(self, result: ExtractionResult[TOutput]) -> None:
        """Save extraction results to cache.

        Args:
            result: ExtractionResult to cache
        """
        try:
            # Create cache structure with metadata
            cache_data = {
                "metadata": CacheMetadata(
                    created_at=datetime.now(),
                    item_count=result.success_count,
                    cache_version="1.0",
                ).model_dump(mode="json"),
                "data": [item.model_dump(mode="json") for item in result.successful],
            }

            with open(self.cache_file, "w", encoding="utf-8") as file:
                json.dump(cache_data, file, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Saved {result.success_count} items to cache: {self.cache_file}"
            )

        except OSError as e:
            self.logger.warning(
                f"Failed to write cache file: {self.cache_file}, error={str(e)}"
            )


__all__ = [
    "BaseStaticExtractor",
    "handle_extraction_error",
]
