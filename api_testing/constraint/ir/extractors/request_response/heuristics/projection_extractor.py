"""
Projection/Expand extractor for fields/include/expand parameter patterns.

Detects conditional field presence based on projection parameters.
"""

from typing import List, Optional

from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.constraint.ir.extractors.common import CandidateConstraint
from api_testing.constraint.ir.extractors.common import calculate_similarity
from api_testing.constraint.ir.extractors.request_response.heuristics.base import (
    BaseHeuristicExtractor,
)


class ProjectionExpandExtractor(BaseHeuristicExtractor):
    """Extracts projection/expand constraints from fields/include/expand parameters.

    Patterns detected:
    - fields=name,email → only name and email in response
    - expand=author → author object present
    - include=comments → comments array present
    """

    def __init__(self):
        """Initialize projection extractor."""
        super().__init__("ProjectionExpandExtractor")

    def extract(
        self,
        operation: OperationProperties,
        response_schema: Optional[ItemProperties] = None,
    ) -> List[CandidateConstraint]:
        """Extract projection/expand constraints.

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

        # Flatten response fields
        response_fields = self._flatten_object_fields(resp_schema)

        if not response_fields:
            return candidates

        # Get query parameters
        query_params = operation.get_query_parameters()

        # Look for projection parameters
        projection_params = [p for p in query_params if p.is_projection_param()]

        for param in projection_params:
            # Check if enum values specify field names
            if param.enum:
                for field_value in param.enum[:5]:  # Limit to first 5
                    matches = self._find_matching_fields(
                        str(field_value), response_fields
                    )

                    for field_path, confidence in matches:
                        # Create implies constraint: if param includes field, then field exists
                        candidate = CandidateConstraint(
                            predicate_kind="implies",
                            predicate_version="v1",
                            predicate_args={
                                "condition": f"$request.query.{param.name} contains '{field_value}'",
                                "consequent": "field_exists",
                                "field": field_path,
                            },
                            selectors=[
                                f"$response.body$.{field_path}",
                            ],
                            selector_types=["jsonpath"],
                            operation_id=(
                                operation.uuid
                                if hasattr(operation, "uuid")
                                else str(operation)
                            ),
                            phase="response",
                            location="body",
                            confidence=confidence * 0.8,  # Reduce for conditional
                            tags=["projection", "expand", "conditional"],
                            extractor_name=self.name,
                        )

                        candidate.add_evidence(
                            source="heuristic",
                            location=f"query_param.{param.name}",
                            snippet=f"Projection parameter '{param.name}' with value '{field_value}' implies field '{field_path}' exists",
                            confidence=confidence * 0.8,
                        )

                        candidates.append(candidate)

            # Check description for mentioned fields
            if param.description:
                desc_lower = param.description.lower()

                # Look for field names in description
                for field_path in list(response_fields.keys())[:10]:  # Limit search
                    field_name = field_path.split(".")[-1]

                    if field_name.lower() in desc_lower:
                        # Create implies constraint
                        candidate = CandidateConstraint(
                            predicate_kind="field_exists",
                            predicate_version="v1",
                            predicate_args={
                                "field": field_path,
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
                            confidence=0.7,
                            tags=["projection", "expand"],
                            extractor_name=self.name,
                            metadata={"conditional_on": param.name},
                        )

                        candidate.add_evidence(
                            source="heuristic",
                            location=f"query_param.{param.name}.description",
                            snippet=f"Projection parameter description mentions field '{field_name}'",
                            confidence=0.7,
                        )

                        candidates.append(candidate)

        return candidates

    @staticmethod
    def _find_matching_fields(
            field_value: str,
        response_fields: dict,
    ) -> List[tuple]:
        """Find response fields matching a projection value.

        Args:
            field_value: Projection value (e.g., "author", "comments")
            response_fields: Dict of field_path -> field_props

        Returns:
            List of (field_path, confidence) tuples
        """
        matches = []

        for field_path, _ in response_fields.items():
            field_name = field_path.split(".")[-1]

            # Calculate similarity
            full_sim = calculate_similarity(field_value, field_path)
            name_sim = calculate_similarity(field_value, field_name)

            similarity = max(full_sim, name_sim)

            if similarity >= 0.7:
                matches.append((field_path, similarity))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:2]


__all__ = ["ProjectionExpandExtractor"]
