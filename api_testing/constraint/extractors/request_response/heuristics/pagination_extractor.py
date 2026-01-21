"""
Pagination extractor for limit/offset/page parameter patterns.

Detects pagination constraints where limit/pageSize parameters
constrain the length of response arrays.
"""

from typing import List, Optional

from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from api_testing.constraint.extractors.request_response.heuristics.base import (
    BaseHeuristicExtractor,
)


class PaginationExtractor(BaseHeuristicExtractor):
    """Extracts pagination constraints from limit/offset/page parameters.

    Patterns detected:
    - limit/pageSize/size parameter constrains array length
    - page + pageSize combination
    - cursor-based pagination presence checks
    """

    def __init__(self):
        """Initialize pagination extractor."""
        super().__init__("PaginationExtractor")

    def extract(
        self,
        operation: OperationProperties,
        response_schema: Optional[ItemProperties] = None,
    ) -> List[CandidateConstraint]:
        """Extract pagination constraints.

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
            return candidates

        array_path, _ = array_info

        # Get query parameters
        query_params = operation.get_query_parameters()

        # Look for limit/pageSize parameters
        limit_params = [p for p in query_params if self._is_limit_param(p.name)]

        for param in limit_params:
            # Create len_le constraint
            candidate = CandidateConstraint(
                predicate_kind="len_le",
                predicate_version="v1",
                predicate_args={
                    "max": f"$request.query.{param.name}",  # Reference to request param
                },
                selectors=[
                    f"$response.body$.{array_path}",
                ],
                selector_types=["jsonpath"],
                operation_id=(
                    operation.uuid if hasattr(operation, "uuid") else str(operation)
                ),
                phase="response",
                location="body",
                confidence=0.95,  # High confidence for pagination
                tags=["pagination", "limit", "array_length"],
                extractor_name=self.name,
            )

            candidate.add_evidence(
                source="heuristic",
                location=f"query_param.{param.name}",
                snippet=f"Pagination parameter '{param.name}' constrains array '{array_path}' length",
                confidence=0.95,
            )

            candidates.append(candidate)

            self.logger.debug(
                f"Pagination constraint detected: {param.name} → len({array_path}) <= {param.name}",
            )

        # Look for cursor fields in response (for cursor-based pagination)
        cursor_params = [p for p in query_params if self._is_cursor_param(p.name)]

        if cursor_params and resp_schema.properties:
            # Check for nextCursor, cursor fields in response
            cursor_fields = [
                "nextCursor",
                "next_cursor",
                "cursor",
                "nextPageToken",
                "next_page_token",
            ]

            for cursor_field in cursor_fields:
                if cursor_field in resp_schema.properties:
                    # Create field_exists constraint (conditional on having more results)
                    candidate = CandidateConstraint(
                        predicate_kind="field_exists",
                        predicate_version="v1",
                        predicate_args={
                            "field": cursor_field,
                        },
                        selectors=[
                            "$response.body$",
                        ],
                        selector_types=["jsonpath"],
                        operation_id=(
                            operation.uuid
                            if hasattr(operation, "uuid")
                            else str(operation)
                        ),
                        phase="response",
                        location="body",
                        confidence=0.8,
                        tags=["pagination", "cursor"],
                        extractor_name=self.name,
                        metadata={"constraint_type": "cursor_presence"},
                    )

                    candidate.add_evidence(
                        source="heuristic",
                        location=f"response.{cursor_field}",
                        snippet=f"Cursor field '{cursor_field}' indicates pagination support",
                        confidence=0.8,
                    )

                    candidates.append(candidate)
                    break  # Only add one cursor constraint

        return candidates

    def _is_limit_param(self, name: str) -> bool:
        """Check if parameter name indicates a limit/size parameter.

        Args:
            name: Parameter name

        Returns:
            True if likely a limit parameter
        """
        name_lower = name.lower()
        return name_lower in [
            "limit",
            "pagesize",
            "page_size",
            "size",
            "maxresults",
            "max_results",
            "count",
            "top",
            "per_page",
            "perpage",
        ]

    def _is_cursor_param(self, name: str) -> bool:
        """Check if parameter name indicates a cursor parameter.

        Args:
            name: Parameter name

        Returns:
            True if likely a cursor parameter
        """
        name_lower = name.lower()
        return "cursor" in name_lower or "token" in name_lower


__all__ = ["PaginationExtractor"]
