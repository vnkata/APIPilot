"""
Search extractor for q/query/search parameter patterns.

Detects search constraints (with low confidence due to fuzzy semantics).
"""

from typing import List, Optional

from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from api_testing.constraint.extractors.request_response.heuristics.base import (
    BaseHeuristicExtractor,
)


class SearchExtractor(BaseHeuristicExtractor):
    """Extracts search constraints from q/query/search/keyword parameters.

    Patterns detected (all with low confidence):
    - q/query/search parameter searches in string fields
    - Typically creates contains_substring constraints
    """

    def __init__(self):
        """Initialize search extractor."""
        super().__init__("SearchExtractor")

    def extract(
        self,
        operation: OperationProperties,
        response_schema: Optional[ItemProperties] = None,
    ) -> List[CandidateConstraint]:
        """Extract search constraints.

        Args:
            operation: Operation to analyze
            response_schema: Optional pre-extracted response schema

        Returns:
            List of candidate constraints
        """
        candidates = []

        # Get response schema
        resp_schema = self._get_response_schema(operation, response_schema)
        if not resp_schema:
            return candidates

        # Find array field in response
        array_info = self._find_array_in_schema(resp_schema)
        if not array_info:
            # Could be searching a single object
            return candidates

        array_path, array_schema = array_info

        # Get item schema
        if not array_schema.items:
            return candidates

        # Flatten item fields
        item_fields = self._flatten_object_fields(array_schema.items)

        # Get query parameters
        query_params = operation.get_query_parameters()

        # Look for search parameters
        search_params = [p for p in query_params if p.is_search_param()]

        for param in search_params:
            # Find string fields in items
            string_fields = [
                field_path
                for field_path, field_props in item_fields.items()
                if field_props.get("type") == "string"
            ]

            if not string_fields:
                continue

            # Create a generic search constraint with low confidence
            # We mark it as warning-only since search semantics are fuzzy
            for field_path in string_fields[:3]:  # Limit to first 3 string fields
                candidate = CandidateConstraint(
                    predicate_kind="contains_substring",
                    predicate_version="v1",
                    predicate_args={
                        "substring": f"$request.query.{param.name}",
                    },
                    selectors=[
                        f"$response.body$.{array_path}[*].{field_path}",
                    ],
                    selector_types=["jsonpath"],
                    operation_id=(
                        operation.uuid if hasattr(operation, "uuid") else str(operation)
                    ),
                    phase="response",
                    location="body",
                    confidence=0.5,  # Low confidence for search
                    tags=["search", "fuzzy", "warning_only"],
                    extractor_name=self.name,
                    metadata={"severity": "warning"},
                )

                candidate.add_evidence(
                    source="heuristic",
                    location=f"query_param.{param.name}",
                    snippet=f"Search parameter '{param.name}' may search in field '{field_path}' (low confidence)",
                    confidence=0.5,
                )

                candidates.append(candidate)

                self.logger.debug(
                    f"Search constraint detected (low confidence): {param.name} → {field_path}",
                )

        return candidates


__all__ = ["SearchExtractor"]
