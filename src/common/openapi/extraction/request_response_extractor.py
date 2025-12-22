"""
Request-response constraints extractor

Maps request bodies to response bodies at the endpoint level.
Uses OpenAPI spec structure without raw text parsing.
"""

from typing import Optional

from common.logger.utils.helpers import get_logger
from common.openapi.extraction.models import EndpointConstraint
from common.openapi.models import SpecDict

logger = get_logger(__name__)


class RequestResponseExtractor:
    """
    Extract endpoint-level request-response mappings from OpenAPI specs

    Maps request bodies to response schemas at the endpoint level.
    Does not attempt field-level mapping (requires semantic analysis).

    Features:
    - Extracts endpoint path and HTTP method
    - Identifies request body component (if any)
    - Identifies response body component (if any)
    - Only uses OpenAPI spec structure (no raw text parsing)
    """

    def __init__(self, spec_dict: SpecDict, spec_name: str) -> None:
        """
        Initialize extractor

        Args:
            spec_dict: Resolved OpenAPI spec as dict
            spec_name: Human-readable name for spec
        """
        self.spec_dict = spec_dict
        self.spec_name = spec_name
        self.paths = spec_dict.get("paths", {})
        self.components = spec_dict.get("components", {})
        self.schemas = self.components.get("schemas", {})

    def extract_all_mappings(self) -> list[EndpointConstraint]:
        """
        Extract all endpoint-level request-response mappings

        Returns:
            List of EndpointConstraint objects
        """
        constraints = []

        # Iterate through all paths and operations
        for path, path_item in self.paths.items():
            if not isinstance(path_item, dict):
                continue

            for method, operation in path_item.items():
                # Skip non-operation items ($ref, parameters, etc.)
                if method.startswith("$") or method in ("parameters", "servers"):
                    continue

                method_upper = method.upper()

                if not isinstance(operation, dict):
                    continue

                try:
                    endpoint_constraints = self._extract_endpoint_mapping(
                        path, method_upper, operation
                    )
                    constraints.extend(endpoint_constraints)
                except Exception as e:
                    logger.warning(
                        f"Error extracting mapping for {method_upper} {path}: {e}",
                        extra={"error_type": type(e).__name__},
                    )

        logger.info(
            f"Extracted {len(constraints)} endpoint mappings from {self.spec_name}"
        )
        return constraints

    def _extract_endpoint_mapping(
        self, path: str, method: str, operation: dict
    ) -> list[EndpointConstraint]:
        """
        Extract request-response mapping from a single operation

        Args:
            path: API endpoint path
            method: HTTP method
            operation: Operation definition dict

        Returns:
            List of EndpointConstraint objects (one per response status)
        """
        constraints = []

        # Extract request body component
        request_body_component = self._get_request_body_component(operation)

        # Extract response mappings
        responses = operation.get("responses", {})

        for status_code, response_def in responses.items():
            if not isinstance(response_def, dict):
                continue

            response_component = self._get_response_component(response_def)

            constraint = EndpointConstraint(
                spec_name=self.spec_name,
                endpoint_path=path,
                http_method=method,
                request_body_component=request_body_component,
                response_component=response_component,
                response_status_code=status_code,
                constraint_notes=(
                    f"Request: {request_body_component or 'No body'} → "
                    f"Response: {response_component or 'No schema'}"
                ),
            )
            constraints.append(constraint)

        return constraints

    def _get_request_body_component(self, operation: dict) -> Optional[str]:
        """
        Extract request body component name from operation

        Args:
            operation: Operation definition dict

        Returns:
            Component name or None
        """
        request_body = operation.get("requestBody")
        if not request_body or not isinstance(request_body, dict):
            return None

        # Get content type (usually application/json)
        content = request_body.get("content", {})
        for media_type, media_def in content.items():
            if not isinstance(media_def, dict):
                continue

            schema = media_def.get("schema")
            if isinstance(schema, dict):
                # Direct schema definition
                if schema.get("type") == "object" and "properties" in schema:
                    # Inline schema, use operation summary or auto-generate name
                    return f"_{operation.get('operationId', 'Request').title()}"

                # Reference to component
                if "$ref" in schema:
                    return schema["$ref"].split("/")[-1]

        return None

    def _get_response_component(self, response_def: dict) -> Optional[str]:
        """
        Extract response schema component name from response definition

        Args:
            response_def: Response definition dict

        Returns:
            Component name or None
        """
        content = response_def.get("content", {})

        for media_type, media_def in content.items():
            if not isinstance(media_def, dict):
                continue

            schema = media_def.get("schema")
            if not schema or not isinstance(schema, dict):
                continue

            # Handle array response
            if schema.get("type") == "array":
                items = schema.get("items", {})
                if isinstance(items, dict) and "$ref" in items:
                    return f"{items['$ref'].split('/')[-1]}[]"
                return "Array"

            # Direct reference
            if "$ref" in schema:
                return schema["$ref"].split("/")[-1]

            # Inline schema
            if schema.get("type") == "object":
                return "_InlineSchema"

        return None


__all__ = ["RequestResponseExtractor"]
