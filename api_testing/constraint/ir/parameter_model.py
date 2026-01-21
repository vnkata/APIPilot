"""
Parameter information models for request-response constraint extraction.

Provides structured types for parameter extraction and matching.
"""

from typing import Any, Optional, Literal
from pydantic import BaseModel, Field


class ParameterInfo(BaseModel):
    """Structured information about an API parameter.

    Represents parameters from path, query, header, or cookie locations
    with their schema, description, and metadata.
    """

    name: str = Field(..., description="Parameter name")
    location: Literal["path", "query", "header", "cookie"] = Field(
        ..., description="Where the parameter appears"
    )
    required: bool = Field(default=False, description="Whether parameter is required")
    schema_type: Optional[str] = Field(
        None, description="Parameter data type (string, integer, etc.)"
    )
    format: Optional[str] = Field(
        None, description="Parameter format (date, uuid, etc.)"
    )
    description: Optional[str] = Field(
        None, description="Parameter description from OpenAPI spec"
    )
    enum: Optional[list] = Field(None, description="Allowed enum values if specified")
    default: Optional[Any] = Field(None, description="Default value if specified")

    # Additional metadata
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    def normalize_name(self) -> str:
        """Normalize parameter name for matching (lowercase, underscore to camel)."""
        # Convert snake_case to camelCase for matching
        parts = self.name.lower().split("_")
        if len(parts) == 1:
            return parts[0]
        return parts[0] + "".join(p.capitalize() for p in parts[1:])

    def is_type_compatible(self, field_type: Optional[str]) -> bool:
        """Check if this parameter is type-compatible with a field type.

        Args:
            field_type: The field type to check against

        Returns:
            True if types are compatible for comparison
        """
        if not field_type or not self.schema_type:
            return False

        # Direct match
        if self.schema_type == field_type:
            return True

        # Compatible numeric types
        if self.schema_type in ["integer", "number"] and field_type in [
            "integer",
            "number",
        ]:
            return True

        # String is compatible with formatted strings (date, uuid, etc.)
        if self.schema_type == "string" and field_type == "string":
            return True

        return False

    def similarity_score(self, field_name: str) -> float:
        """Calculate similarity score with a field name.

        Args:
            field_name: The field name to compare against

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Exact match
        if self.name == field_name:
            return 1.0

        # Case-insensitive match
        if self.name.lower() == field_name.lower():
            return 0.9

        # Normalized match (camelCase vs snake_case)
        norm_param = self.normalize_name()
        norm_field = field_name.lower().replace("_", "")
        if norm_param == norm_field:
            return 0.85

        # Substring match
        if (
            self.name.lower() in field_name.lower()
            or field_name.lower() in self.name.lower()
        ):
            return 0.7

        # Common prefix/suffix patterns
        # e.g., userId vs user.id, provinceId vs province.id
        param_lower = self.name.lower()
        field_lower = field_name.lower().replace(".", "").replace("_", "")

        if param_lower.endswith("id") and field_lower.endswith("id"):
            param_base = param_lower[:-2]
            field_base = field_lower[:-2]
            if param_base in field_base or field_base in param_base:
                return 0.75

        return 0.0

    def is_likely_id_field(self) -> bool:
        """Check if this parameter is likely an ID field."""
        name_lower = self.name.lower()
        return (
            name_lower.endswith("id")
            or name_lower.endswith("_id")
            or name_lower == "id"
            or "identifier" in name_lower
        )

    def is_filter_param(self) -> bool:
        """Check if this parameter is likely a filter parameter."""
        if self.location != "query":
            return False

        # Check description for filter keywords
        desc_lower = (self.description or "").lower()
        filter_keywords = ["filter", "by", "match", "equals", "where"]
        return any(kw in desc_lower for kw in filter_keywords)

    def is_pagination_param(self) -> bool:
        """Check if this parameter is likely a pagination parameter."""
        if self.location != "query":
            return False

        name_lower = self.name.lower()
        pagination_names = [
            "limit",
            "pagesize",
            "page_size",
            "size",
            "offset",
            "page",
            "cursor",
            "nextcursor",
            "next_cursor",
            "pageindex",
            "page_index",
        ]
        return name_lower in pagination_names

    def is_sort_param(self) -> bool:
        """Check if this parameter is likely a sort parameter."""
        if self.location != "query":
            return False

        name_lower = self.name.lower()
        sort_names = [
            "sort",
            "sortby",
            "sort_by",
            "orderby",
            "order_by",
            "order",
            "direction",
            "dir",
            "asc",
            "desc",
        ]
        return name_lower in sort_names

    def is_search_param(self) -> bool:
        """Check if this parameter is likely a search parameter."""
        if self.location != "query":
            return False

        name_lower = self.name.lower()
        search_names = ["q", "query", "search", "keyword", "keywords", "term"]
        return name_lower in search_names

    def is_projection_param(self) -> bool:
        """Check if this parameter is likely a projection/expand parameter."""
        if self.location != "query":
            return False

        name_lower = self.name.lower()
        projection_names = ["fields", "select", "include", "expand", "embed", "with"]
        return name_lower in projection_names


__all__ = ["ParameterInfo"]
