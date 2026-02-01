"""
Filter extractor for query parameter filtering patterns.

Detects patterns where query parameters filter response arrays,
e.g., GET /items?status=ACTIVE → all response items have status=ACTIVE
"""

from api_testing.constraint.ir.extractors.common import (
    CandidateConstraint,
    calculate_similarity,
)
from api_testing.constraint.ir.extractors.request_response.heuristics.base import (
    BaseHeuristicExtractor,
)
from api_testing.models.specification_model import ItemProperties, OperationProperties


class FilterExtractor(BaseHeuristicExtractor):
    """Extracts filter constraints where query params filter response arrays.

    Patterns detected:
    - Query param 'status' filters items by status field
    - Query param 'userId' filters items by userId field
    - Query param 'type' filters items by type field
    """

    def __init__(self):
        """Initialize filter extractor."""
        super().__init__("FilterExtractor")

    def extract(
        self,
        operation: OperationProperties,
        response_schema: ItemProperties | None = None,
    ) -> list[CandidateConstraint]:
        """Extract filter constraints.

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

        for param in query_params:
            # Skip non-filter params
            if (
                param.is_pagination_param()
                or param.is_sort_param()
                or param.is_search_param()
                or param.is_projection_param()
            ):
                continue

            # Find matching item fields
            matches = self._find_matching_item_fields(
                param.name,
                param.schema_type,
                param.description,
                item_fields,
            )

            for field_path, confidence in matches:
                # Create forall_eq constraint
                candidate = CandidateConstraint(
                    predicate_kind="forall_eq",
                    predicate_version="v1",
                    predicate_args={
                        "expected": f"$request.query.{param.name}",  # Reference to request param
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
                    confidence=confidence,
                    tags=["filter", "query_param", "array"],
                    extractor_name=self.name,
                )

                # Add evidence
                evidence_snippet = f"Query parameter '{param.name}' filters array '{array_path}' by field '{field_path}'"
                if param.description and (
                    "filter" in param.description.lower()
                    or "by" in param.description.lower()
                ):
                    evidence_snippet += " (description mentions filtering)"

                candidate.add_evidence(
                    source="heuristic",
                    location=f"query_param.{param.name}",
                    snippet=evidence_snippet,
                    confidence=confidence,
                )

                candidates.append(candidate)

                self.logger.debug(
                    f"Filter constraint detected: {param.name} → {array_path}[*].{field_path}",
                    confidence=confidence,
                )

        return candidates

    @staticmethod
    def _find_matching_item_fields(
        param_name: str,
        param_type: str | None,
        param_description: str | None,
        item_fields: dict,
    ) -> list[tuple]:
        """Find item fields that match a filter parameter.

        Args:
            param_name: Parameter name
            param_type: Parameter type
            param_description: Parameter description
            item_fields: Dict of field_path -> field_props

        Returns:
            List of (field_path, confidence) tuples
        """
        matches = []

        for field_path, field_props in item_fields.items():
            field_name = field_path.split(".")[-1]

            # Calculate name similarity
            full_path_sim = calculate_similarity(param_name, field_path)
            field_name_sim = calculate_similarity(param_name, field_name)

            name_similarity = max(full_path_sim, field_name_sim)

            if name_similarity < 0.6:
                continue

            # Check type compatibility
            type_bonus = 0.0
            if param_type and field_props.get("type"):
                if param_type == field_props["type"]:
                    type_bonus = 0.15

            # Check description for filter keywords
            description_bonus = 0.0
            if param_description:
                desc_lower = param_description.lower()
                if any(kw in desc_lower for kw in ["filter", "by", "match", "where"]):
                    description_bonus = 0.1

            # Calculate overall confidence
            confidence = min(1.0, name_similarity + type_bonus + description_bonus)

            if confidence >= 0.65:
                matches.append((field_path, confidence))

        # Sort by confidence
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches[:2]  # Top 2 matches


__all__ = ["FilterExtractor"]
