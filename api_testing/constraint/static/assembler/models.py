"""Pydantic models for unified constraint structure.

Defines strongly-typed models for the new unified constraints format.
"""

from pydantic import BaseModel, Field


class ResponsePropertyConstraint(BaseModel):
    """Constraint data for a single response property.

    Contains both request-response relationships and response property
    metadata for a specific field in the API response.

    Attributes:
        request: Dict mapping parameter names to enhanced constraint descriptions.
                 Descriptions include parameter schema info and constraint relationship.
        response_property: Description of the response property itself

    Example:
        >>> constraint = ResponsePropertyConstraint(
        ...     request={
        ...         "year": "[year: a integer parameter...] Request parameter 'year' filters..."
        ...     },
        ...     response_property="ISO date format, e.g., 2020-12-26"
        ... )
    """

    request: dict[str, str] = Field(
        default_factory=dict,
        description="Request parameter constraints (param_name -> enhanced_description)",
    )
    response_property: str = Field(
        ..., description="Response property constraint description"
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        extra = "forbid"


class UnifiedConstraints(BaseModel):
    """Unified constraints structure for an API operation.

    Combines body-level constraints (affecting entire response structure)
    and detail-level constraints (affecting specific response properties).

    Attributes:
        body: Dict of request parameters affecting entire response body
              (pagination, sorting, search, filtering)
        detail: Dict mapping response property paths to their constraints

    Example:
        >>> constraints = UnifiedConstraints(
        ...     body={
        ...         "limit": "Limits number of results returned",
        ...         "sort": "Sorts response by specified field"
        ...     },
        ...     detail={
        ...         "holidays.date": ResponsePropertyConstraint(
        ...             request=[RequestConstraintItem(...)],
        ...             response_property="..."
        ...         )
        ...     }
        ... )
    """

    body: dict[str, str] = Field(
        default_factory=dict,
        description="Request parameters affecting entire response body structure",
    )
    detail: dict[str, ResponsePropertyConstraint] = Field(
        default_factory=dict,
        description="Response property constraints with request relationships",
    )

    class Config:
        """Pydantic model configuration."""

        frozen = False
        extra = "forbid"

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "body": self.body,
            "detail": {
                prop_path: {
                    "request": constraint.request,  # Already Dict[str, str]
                    "response_property": constraint.response_property,
                }
                for prop_path, constraint in self.detail.items()
            },
        }


__all__ = [
    "ResponsePropertyConstraint",
    "UnifiedConstraints",
]
