"""
Sort extractor for sort/orderBy parameter patterns.

Detects sorting constraints where sort parameters specify
the order of response arrays.
"""

import re

from api_testing.constraint.ir.extractors.common import (
    CandidateConstraint,
    calculate_similarity,
)
from api_testing.constraint.ir.extractors.request_response.heuristics.base import (
    BaseHeuristicExtractor,
)
from api_testing.models.specification_model import ItemProperties, OperationProperties


class SortExtractor(BaseHeuristicExtractor):
    """Extracts sort constraints from sort/orderBy parameters.

    Patterns detected:
    - sort=createdAt, sortBy=name, orderBy=id
    - Sort direction: -createdAt, createdAt:desc, createdAt,desc
    - Multiple sort keys
    """

    def __init__(self):
        """Initialize sort extractor."""
        super().__init__("SortExtractor")

    def extract(
        self,
        operation: OperationProperties,
        response_schema: ItemProperties | None = None,
    ) -> list[CandidateConstraint]:
        """Extract sort constraints.

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

        array_path, array_schema = array_info

        # Get item schema
        if not array_schema.items:
            return candidates

        # Flatten item fields
        item_fields = self._flatten_object_fields(array_schema.items)

        if not item_fields:
            return candidates

        # Get query parameters
        query_params = operation.get_query_parameters()

        # Look for sort parameters
        sort_params = [p for p in query_params if p.is_sort_param()]

        for param in sort_params:
            # Try to parse sort field and direction from description
            sort_info = self._parse_sort_info(
                param.name, param.description, item_fields
            )

            if not sort_info:
                # Generic sort constraint (field name from description or enum)
                if param.enum:
                    # If enum values provided, match against item fields
                    for enum_value in param.enum[:3]:  # Limit to first 3
                        matches = self._find_sortable_field(
                            str(enum_value), item_fields
                        )
                        for field_path, confidence in matches:
                            candidate = self._create_sort_candidate(
                                operation,
                                param.name,
                                array_path,
                                field_path,
                                direction="asc",  # Default
                                confidence=confidence * 0.85,  # Reduce for enum guess
                            )
                            candidates.append(candidate)
                continue

            field_name, direction = sort_info

            # Find matching field in item schema
            matches = self._find_sortable_field(field_name, item_fields)

            for field_path, confidence in matches:
                candidate = self._create_sort_candidate(
                    operation,
                    param.name,
                    array_path,
                    field_path,
                    direction=direction,
                    confidence=confidence,
                )
                candidates.append(candidate)

        return candidates

    @staticmethod
    def _parse_sort_info(
        param_name: str,
        param_description: str | None,
        item_fields: dict,
    ) -> tuple[str, str] | None:
        """Parse sort field name and direction from parameter.

        Args:
            param_name: Parameter name
            param_description: Parameter description
            item_fields: Item fields

        Returns:
            Tuple of (field_name, direction) or None
        """
        # Check if param name itself contains field (e.g., sortByName)
        if param_name.lower().startswith("sortby"):
            field_name = param_name[6:]  # Remove "sortby"
            if field_name:
                return (field_name, "asc")

        if param_name.lower().startswith("orderby"):
            field_name = param_name[7:]  # Remove "orderby"
            if field_name:
                return (field_name, "asc")

        # Check description for field names
        if param_description:
            desc_lower = param_description.lower()

            # Look for "sort by <field>" patterns
            sort_by_match = re.search(r"sort\s+by\s+(\w+)", desc_lower)
            if sort_by_match:
                return (sort_by_match.group(1), "asc")

            # Look for field names mentioned in description
            for field_path in item_fields.keys():
                field_name = field_path.split(".")[-1]
                if field_name.lower() in desc_lower:
                    # Check for direction keywords
                    direction = "asc"
                    if any(
                        kw in desc_lower for kw in ["desc", "descending", "reverse"]
                    ):
                        direction = "desc"
                    return (field_name, direction)

        return None

    @staticmethod
    def _find_sortable_field(
        field_name: str,
        item_fields: dict,
    ) -> list[tuple[str, float]]:
        """Find item fields that could be the sort field.

        Args:
            field_name: Field name to search for
            item_fields: Dict of field_path -> field_props

        Returns:
            List of (field_path, confidence) tuples
        """
        matches = []

        for field_path, field_props in item_fields.items():
            field_last = field_path.split(".")[-1]

            # Calculate similarity
            full_sim = calculate_similarity(field_name, field_path)
            last_sim = calculate_similarity(field_name, field_last)

            similarity = max(full_sim, last_sim)

            if similarity < 0.6:
                continue

            # Bonus for sortable types (numbers, dates, strings)
            type_bonus = 0.0
            field_type = field_props.get("type")
            if field_type in ["integer", "number", "string"]:
                type_bonus = 0.05

            # Bonus for date/timestamp fields
            if field_props.get("format") in ["date", "date-time", "datetime"]:
                type_bonus = 0.1

            confidence = min(1.0, similarity + type_bonus)

            if confidence >= 0.65:
                matches.append((field_path, confidence))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:2]

    def _create_sort_candidate(
        self,
        operation: OperationProperties,
        param_name: str,
        array_path: str,
        field_path: str,
        direction: str,
        confidence: float,
    ) -> CandidateConstraint:
        """Create a sort candidate constraint.

        Args:
            operation: Operation
            param_name: Sort parameter name
            array_path: Response array path
            field_path: Item field path to sort by
            direction: Sort direction (asc/desc)
            confidence: Confidence score

        Returns:
            CandidateConstraint
        """
        candidate = CandidateConstraint(
            predicate_kind="sorted_by",
            predicate_version="v1",
            predicate_args={
                "field": field_path,
                "direction": direction,
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
            confidence=confidence,
            tags=["sort", "ordering", "array"],
            extractor_name=self.name,
        )

        candidate.add_evidence(
            source="heuristic",
            location=f"query_param.{param_name}",
            snippet=f"Sort parameter '{param_name}' orders array '{array_path}' by '{field_path}' ({direction})",
            confidence=confidence,
        )

        self.logger.debug(
            f"Sort constraint detected: {param_name} → sorted_by({field_path}, {direction})",
        )

        return candidate


__all__ = ["SortExtractor"]
