"""
Range extractor for startDate/endDate, minValue/maxValue parameter pairs.

Detects range constraints where paired parameters define bounds.
"""

from typing import List, Optional, Tuple
import re

from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from api_testing.constraint.extractors.common.name_matching import (
    calculate_similarity,
    are_related_by_naming,
)
from api_testing.constraint.extractors.request_response.heuristics.base import (
    BaseHeuristicExtractor,
)


class RangeExtractor(BaseHeuristicExtractor):
    """Extracts range constraints from paired min/max, start/end parameters.

    Patterns detected:
    - startDate/endDate parameters define date range
    - minPrice/maxPrice parameters define price range
    - Also creates cross-field request constraint: start < end
    """

    def __init__(self):
        """Initialize range extractor."""
        super().__init__("RangeExtractor")

    def extract(
        self,
        operation: OperationProperties,
        response_schema: Optional[ItemProperties] = None,
    ) -> List[CandidateConstraint]:
        """Extract range constraints.

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

        # Get query parameters
        query_params = operation.get_query_parameters()

        # Find range parameter pairs
        range_pairs = self._find_range_pairs(query_params)

        if not range_pairs:
            return candidates

        # Process each range pair
        for start_param, end_param, base_name in range_pairs:
            # First, create cross-field request constraint (start < end)
            request_constraint = CandidateConstraint(
                predicate_kind="comparison.less_than_or_equal",
                predicate_version="v1",
                predicate_args={},
                selectors=[
                    f"$request.query.{start_param.name}",
                    f"$request.query.{end_param.name}",
                ],
                selector_types=["request_ref", "request_ref"],
                operation_id=(
                    operation.uuid if hasattr(operation, "uuid") else str(operation)
                ),
                phase="request",
                location="query",
                confidence=0.95,
                tags=["range", "request_validation", "cross_field"],
                extractor_name=self.name,
            )

            request_constraint.add_evidence(
                source="heuristic",
                location=f"query_params.{start_param.name},{end_param.name}",
                snippet=f"Range parameters '{start_param.name}' and '{end_param.name}' must satisfy: {start_param.name} <= {end_param.name}",
                confidence=0.95,
            )

            candidates.append(request_constraint)

            # If there's a response array, create response range constraint
            if array_info:
                array_path, array_schema = array_info

                if not array_schema.items:
                    continue

                # Flatten item fields
                item_fields = self._flatten_object_fields(array_schema.items)

                # Find matching field in response
                matches = self._find_range_field(base_name, item_fields)

                for field_path, confidence in matches:
                    field_type = item_fields[field_path].get("type")
                    field_format = item_fields[field_path].get("format")

                    # Determine predicate based on type
                    if (
                        field_format in ["date", "date-time", "datetime"]
                        or field_type == "string"
                    ):
                        predicate_kind = "date_in_range"
                    elif field_type in ["integer", "number"]:
                        predicate_kind = "comparison.between"
                    else:
                        continue

                    response_constraint = CandidateConstraint(
                        predicate_kind=predicate_kind,
                        predicate_version="v1",
                        predicate_args=(
                            {
                                "start": f"$request.query.{start_param.name}",
                                "end": f"$request.query.{end_param.name}",
                            }
                            if predicate_kind == "date_in_range"
                            else {
                                "min": f"$request.query.{start_param.name}",
                                "max": f"$request.query.{end_param.name}",
                            }
                        ),
                        selectors=[
                            f"$response.body$.{array_path}[*].{field_path}",
                        ],
                        selector_types=["jsonpath"],
                        operation_id=(
                            operation.uuid
                            if hasattr(operation, "uuid")
                            else str(operation)
                        ),
                        phase="response",
                        location="body",
                        confidence=confidence,
                        tags=["range", "filter", "array"],
                        extractor_name=self.name,
                    )

                    response_constraint.add_evidence(
                        source="heuristic",
                        location=f"query_params.{start_param.name},{end_param.name}",
                        snippet=f"Range parameters filter array '{array_path}' by field '{field_path}'",
                        confidence=confidence,
                    )

                    candidates.append(response_constraint)

        return candidates

    def _find_range_pairs(self, query_params) -> List[Tuple]:
        """Find pairs of range parameters (start/end, min/max).

        Args:
            query_params: List of ParameterInfo

        Returns:
            List of (start_param, end_param, base_name) tuples
        """
        pairs = []

        # Common range patterns
        patterns = [
            (r"^start(.*)$", r"^end(.*)$"),  # startDate/endDate
            (r"^min(.*)$", r"^max(.*)$"),  # minPrice/maxPrice
            (r"^from(.*)$", r"^to(.*)$"),  # fromDate/toDate
            (r"^(.*)_start$", r"^(.*)_end$"),  # date_start/date_end
            (r"^(.*)_min$", r"^(.*)_max$"),  # price_min/price_max
        ]

        for start_pattern, end_pattern in patterns:
            for start_param in query_params:
                start_match = re.match(start_pattern, start_param.name, re.IGNORECASE)

                if not start_match:
                    continue

                base_name = start_match.group(1) if start_match.lastindex else ""

                # Find matching end parameter
                for end_param in query_params:
                    if end_param.name == start_param.name:
                        continue

                    end_match = re.match(end_pattern, end_param.name, re.IGNORECASE)

                    if not end_match:
                        continue

                    end_base = end_match.group(1) if end_match.lastindex else ""

                    # Check if base names match
                    if base_name.lower() == end_base.lower():
                        # Check if types are compatible
                        if start_param.is_type_compatible(end_param.schema_type):
                            pairs.append((start_param, end_param, base_name or "value"))
                            break

        return pairs

    def _find_range_field(
        self,
        base_name: str,
        item_fields: dict,
    ) -> List[Tuple[str, float]]:
        """Find item fields matching the range base name.

        Args:
            base_name: Base name extracted from range params
            item_fields: Dict of field_path -> field_props

        Returns:
            List of (field_path, confidence) tuples
        """
        matches = []

        for field_path, _ in item_fields.items():
            field_name = field_path.split(".")[-1]

            # Calculate similarity
            if not base_name:
                continue

            full_sim = calculate_similarity(base_name, field_path)
            name_sim = calculate_similarity(base_name, field_name)

            similarity = max(full_sim, name_sim)

            if similarity >= 0.6 or are_related_by_naming(base_name, field_name):
                matches.append((field_path, min(0.9, similarity + 0.1)))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:2]


__all__ = ["RangeExtractor"]
