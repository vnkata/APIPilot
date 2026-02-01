"""Pydantic models for static constraint extraction.

Defines strongly-typed models for intermediate and final results
during static constraint extraction pipeline.
"""

from datetime import datetime
from typing import Any, TypeVar

from pydantic import BaseModel, Field


class SchemaConstraints(BaseModel):
    """Constraints extracted from a single schema.

    Maps attribute paths to their constraint descriptions.
    Used as intermediate format before converting to operation-level constraints.

    Example:
        >>> constraints = SchemaConstraints(
        ...     schema_name="HolidayResponse",
        ...     constraints={
        ...         "date": "ISO date format, e.g., 2020-12-26",
        ...         "nameEn": "English name of the holiday"
        ...     }
        ... )
    """

    schema_name: str = Field(..., description="Name of the schema")
    constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Attribute path to constraint description mapping",
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        extra = "forbid"


class OperationConstraints(BaseModel):
    """Response property constraints for a single operation.

    Maps response property paths to their constraint descriptions.
    Operation-level view of schema constraints.

    Example:
        >>> constraints = OperationConstraints(
        ...     operation_uuid="get-/api/v1/holidays",
        ...     constraints={
        ...         "holidays.date": "ISO date format, e.g., 2020-12-26",
        ...         "holidays.nameEn": "English name of the holiday"
        ...     }
        ... )
    """

    operation_uuid: str = Field(..., description="UUID of the operation")
    constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Response property path to constraint description mapping",
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        extra = "forbid"


class RequestResponseConstraints(BaseModel):
    """Request-response constraints for a single operation.

    Nested structure mapping request parameters to response properties
    they constrain, with relationship descriptions.

    Example:
        >>> constraints = RequestResponseConstraints(
        ...     operation_uuid="get-/api/v1/holidays",
        ...     constraints={
        ...         "year": {
        ...             "holidays.date": "Filters holidays to specified year",
        ...             "holidays.observedDate": "Observed date within year"
        ...         },
        ...         "provinceId": {
        ...             "province": "Returns province with matching ID"
        ...         }
        ...     }
        ... )
    """

    operation_uuid: str = Field(..., description="UUID of the operation")
    constraints: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description=(
            "Request parameter -> Response property -> Constraint description mapping"
        ),
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        extra = "forbid"


T = TypeVar("T", bound=BaseModel)


class ExtractionResult[T: BaseModel](BaseModel):
    """Result of batch extraction with success/failure tracking.

    Generic wrapper for extraction results that tracks both successful
    extractions and failures for observability.

    Example:
        >>> result = ExtractionResult[SchemaConstraints](
        ...     successful=[
        ...         SchemaConstraints(schema_name="Holiday", constraints={...}),
        ...         SchemaConstraints(schema_name="Province", constraints={...})
        ...     ],
        ...     failed=[("InvalidSchema", "LLMError: timeout")],
        ...     total_processed=3
        ... )
    """

    successful: list[T] = Field(
        default_factory=list, description="Successfully extracted items"
    )
    failed: list[tuple[str, str]] = Field(
        default_factory=list,
        description="Failed items as (identifier, error_message) tuples",
    )
    total_processed: int = Field(
        ..., description="Total number of items attempted", ge=0
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        extra = "forbid"

    @property
    def success_count(self) -> int:
        """Number of successfully extracted items."""
        return len(self.successful)

    @property
    def failure_count(self) -> int:
        """Number of failed extractions."""
        return len(self.failed)

    @property
    def success_rate(self) -> float:
        """Success rate as percentage (0.0 to 1.0)."""
        if self.total_processed == 0:
            return 0.0
        return self.success_count / self.total_processed


class CacheMetadata(BaseModel):
    """Metadata for cache files.

    Tracks cache creation time and optional version information
    for cache invalidation strategies.

    Example:
        >>> metadata = CacheMetadata(
        ...     created_at=datetime.now(),
        ...     item_count=42
        ... )
    """

    created_at: datetime = Field(
        default_factory=datetime.now, description="Timestamp when cache was created"
    )
    item_count: int = Field(..., description="Number of items in cache", ge=0)
    cache_version: str | None = Field(
        default=None, description="Optional cache format version"
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        extra = "forbid"


class OperationConstraintsData(BaseModel):
    """Unified constraints data for a single operation.

    Contains both response property constraints and request-response constraints,
    plus the new unified constraints structure.
    """

    response_properties_constraints: dict[str, str] = Field(
        default_factory=dict,
        description="Maps response property paths to constraint descriptions (legacy)",
    )

    request_response_constraints: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Maps request parameters to response properties with constraint descriptions (legacy)",
    )

    constraints: dict[str, Any] | None = Field(
        default=None,
        description="Unified constraint structure with body and detail sections",
    )


class StaticConstraintMinerOutput(BaseModel):
    """Complete output from StaticConstraintMiner.

    Groups all constraints by operation UUID, with each operation containing
    both response property constraints and request-response constraints.
    """

    operations: dict[str, OperationConstraintsData] = Field(
        default_factory=dict,
        description="Maps operation UUIDs to their constraint data",
    )


__all__ = [
    "SchemaConstraints",
    "OperationConstraints",
    "RequestResponseConstraints",
    "ExtractionResult",
    "CacheMetadata",
    "OperationConstraintsData",
    "StaticConstraintMinerOutput",
]
