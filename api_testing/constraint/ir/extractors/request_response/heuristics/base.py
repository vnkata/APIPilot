"""
Base heuristic extractor protocol for request-response constraints.

Defines the interface and common utilities for deterministic pattern-based extractors.
"""

from typing import List, Protocol, Optional
from abc import abstractmethod

from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.constraint.ir.extractors.common import CandidateConstraint
from common.logger import get_logger

logger = get_logger(__name__)


class HeuristicExtractor(Protocol):
    """Protocol for heuristic extractors.

    Heuristic extractors use deterministic pattern matching to detect
    request-response constraints (echo, filter, pagination, sort, etc.)
    """

    @property
    def name(self) -> str:
        """Extractor name for logging and metadata."""
        ...

    @abstractmethod
    def extract(
        self,
        operation: OperationProperties,
        response_schema: Optional[ItemProperties] = None,
    ) -> List[CandidateConstraint]:
        """Extract candidate constraints from an operation.

        Args:
            operation: The operation to analyze
            response_schema: Optional response schema (will be extracted if not provided)

        Returns:
            List of candidate constraints
        """
        ...


class BaseHeuristicExtractor:
    """Base class for heuristic extractors with common utilities."""

    def __init__(self, name: str):
        """Initialize base extractor.

        Args:
            name: Extractor name
        """
        self._name = name
        self.logger = logger

    @property
    def name(self) -> str:
        """Extractor name."""
        return self._name

    @staticmethod
    def _get_response_schema(
            operation: OperationProperties,
        provided_schema: Optional[ItemProperties] = None,
    ) -> Optional[ItemProperties]:
        """Get response schema, using provided or extracting from operation.

        Args:
            operation: Operation to extract from
            provided_schema: Pre-extracted schema if available

        Returns:
            Response schema or None
        """
        if provided_schema:
            return provided_schema

        return operation.get_success_response_schema()

    @staticmethod
    def _find_array_in_schema(
            schema: ItemProperties,
        preferred_names: List[str] = None,
    ) -> Optional[tuple]:
        """Find an array field in the schema.

        Args:
            schema: Schema to search
            preferred_names: Preferred field names to look for first

        Returns:
            Tuple of (field_path, array_schema) or None
        """
        if not schema:
            return None

        preferred_names = preferred_names or ["items", "data", "results", "list"]

        # Check top-level preferred names first
        if schema.properties:
            for name in preferred_names:
                if name in schema.properties:
                    field = schema.properties[name]
                    if field.type == "array":
                        return (name, field)

            # Then check any array field
            for name, field in schema.properties.items():
                if field.type == "array":
                    return (name, field)

        return None

    def _flatten_object_fields(
        self,
        schema: ItemProperties,
        prefix: str = "",
    ) -> dict:
        """Flatten object schema fields into a dict of path -> field_props.

        Args:
            schema: Schema to flatten
            prefix: Path prefix

        Returns:
            Dict mapping field paths to field properties
        """
        result = {}

        if not schema or not schema.properties:
            return result

        for field_name, field_schema in schema.properties.items():
            field_path = f"{prefix}.{field_name}" if prefix else field_name

            # Store field info
            result[field_path] = {
                "type": field_schema.type,
                "format": field_schema.format,
                "description": field_schema.description,
                "enum": field_schema.enum if field_schema.enum else None,
            }

            # Recursively flatten nested objects
            if field_schema.type == "object" and field_schema.properties:
                nested = self._flatten_object_fields(field_schema, field_path)
                result.update(nested)

        return result


__all__ = ["HeuristicExtractor", "BaseHeuristicExtractor"]
