"""
Echo/Identity extractor for request-response constraints.

Detects patterns where path/query parameters echo back in the response,
e.g., GET /users/{id} → response.id or GET /items?userId=X → response.userId
"""

from api_testing.constraint.ir.extractors.common import (
    CandidateConstraint,
    calculate_similarity,
)
from api_testing.constraint.ir.extractors.request_response.heuristics.base import (
    BaseHeuristicExtractor,
)
from api_testing.models.specification_model import ItemProperties, OperationProperties


class EchoIdentityExtractor(BaseHeuristicExtractor):
    """Extracts echo/identity constraints where request params match response fields.

    Patterns detected:
    - Path param {id} matches response.id
    - Path param {userId} matches response.user.id or response.userId
    - Query param status matches response.status
    """

    def __init__(self):
        """Initialize echo extractor."""
        super().__init__("EchoIdentityExtractor")

    def extract(
        self,
        operation: OperationProperties,
        response_schema: ItemProperties | None = None,
    ) -> list[CandidateConstraint]:
        """Extract echo/identity constraints.

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

        # Flatten response fields for matching
        response_fields = self._flatten_object_fields(resp_schema)

        if not response_fields:
            return candidates

        # Extract path parameters
        path_params = operation.get_path_parameters()

        # Match each path parameter against response fields
        for param in path_params:
            matches = self._find_matching_fields(
                param.name,
                param.schema_type,
                response_fields,
            )

            for field_path, confidence in matches:
                # Create candidate constraint
                candidate = CandidateConstraint(
                    predicate_kind="comparison.equals",
                    predicate_version="v1",
                    predicate_args={},
                    selectors=[
                        f"$request.path.{param.name}",
                        f"$response.body$.{field_path}",
                    ],
                    selector_types=["request_ref", "jsonpath"],
                    operation_id=(
                        operation.uuid if hasattr(operation, "uuid") else str(operation)
                    ),
                    phase="response",
                    location="body",
                    confidence=confidence,
                    tags=["echo", "identity", "path_param"],
                    extractor_name=self.name,
                )

                # Add evidence
                candidate.add_evidence(
                    source="heuristic",
                    location=f"path_param.{param.name}",
                    snippet=f"Path parameter '{param.name}' likely matches response field '{field_path}'",
                    confidence=confidence,
                )

                candidates.append(candidate)

                self.logger.debug(
                    f"Echo constraint detected: {param.name} → {field_path}",
                    confidence=confidence,
                    operation=(
                        operation.operation_id
                        if hasattr(operation, "operation_id")
                        else "unknown"
                    ),
                )

        # Also check query parameters (lower priority than path params)
        query_params = operation.get_query_parameters()

        for param in query_params:
            # Skip pagination/sort/search params (handled by other extractors)
            if (
                param.is_pagination_param()
                or param.is_sort_param()
                or param.is_search_param()
            ):
                continue

            matches = self._find_matching_fields(
                param.name,
                param.schema_type,
                response_fields,
                confidence_penalty=0.1,  # Lower confidence for query params
            )

            for field_path, confidence in matches:
                # Only include if confidence is reasonably high
                if confidence < 0.65:
                    continue

                candidate = CandidateConstraint(
                    predicate_kind="comparison.equals",
                    predicate_version="v1",
                    predicate_args={},
                    selectors=[
                        f"$request.query.{param.name}",
                        f"$response.body$.{field_path}",
                    ],
                    selector_types=["request_ref", "jsonpath"],
                    operation_id=(
                        operation.uuid if hasattr(operation, "uuid") else str(operation)
                    ),
                    phase="response",
                    location="body",
                    confidence=confidence,
                    tags=["echo", "identity", "query_param"],
                    extractor_name=self.name,
                )

                candidate.add_evidence(
                    source="heuristic",
                    location=f"query_param.{param.name}",
                    snippet=f"Query parameter '{param.name}' likely matches response field '{field_path}'",
                    confidence=confidence,
                )

                candidates.append(candidate)

        return candidates

    @staticmethod
    def _find_matching_fields(
        param_name: str,
        param_type: str | None,
        response_fields: dict,
        confidence_penalty: float = 0.0,
    ) -> list[tuple]:
        """Find response fields that match a parameter.

        Args:
            param_name: Parameter name
            param_type: Parameter type
            response_fields: Dict of field_path -> field_props
            confidence_penalty: Amount to reduce confidence by

        Returns:
            List of (field_path, confidence) tuples
        """
        matches = []

        for field_path, field_props in response_fields.items():
            # Calculate name similarity
            # Try matching against full path and just field name
            field_name = field_path.split(".")[-1]

            # Calculate similarity
            full_path_sim = calculate_similarity(param_name, field_path)
            field_name_sim = calculate_similarity(param_name, field_name)

            name_similarity = max(full_path_sim, field_name_sim)

            if name_similarity < 0.6:
                continue

            # Check type compatibility (if types are known)
            type_bonus = 0.0
            if param_type and field_props.get("type"):
                if param_type == field_props["type"]:
                    type_bonus = 0.1
                elif param_type in ["integer", "number"] and field_props["type"] in [
                    "integer",
                    "number",
                ]:
                    type_bonus = 0.05

            # Calculate overall confidence
            confidence = min(1.0, name_similarity + type_bonus - confidence_penalty)

            # Only include matches above threshold
            if confidence >= 0.65:
                matches.append((field_path, confidence))

        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)

        # Return top 3 matches to avoid too many candidates
        return matches[:3]


__all__ = ["EchoIdentityExtractor"]
