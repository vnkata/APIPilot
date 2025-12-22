"""
Test data generation from OpenAPI schemas

This module generates test data from OpenAPI schemas using
hypothesis and schemathesis for property-based testing.
"""

from typing import Any, Optional, Union

from hypothesis_jsonschema import from_schema

from common.logger.utils.helpers import get_logger
from common.openapi.exceptions import TestGenerationError
from common.openapi.introspection import EndpointInfo, SpecIntrospector
from common.openapi.models import OpenAPI, Schema

logger = get_logger(__name__)


class TestDataGenerator:
    """
    Generate test data from OpenAPI schemas

    Supports:
    - Random valid data generation from schemas
    - Property-based testing with hypothesis
    - Request body generation
    - Parameter generation
    """

    def __init__(self, spec: OpenAPI) -> None:
        """
        Initialize test data generator

        Args:
            spec: Parsed OpenAPI specification
        """
        self.spec = spec
        self.introspector = SpecIntrospector(spec)

    def generate_from_schema(
        self,
        schema: Schema,
        count: int = 1,
    ) -> Union[Any, list[Any]]:
        """
        Generate test data from a schema

        Args:
            schema: OpenAPI Schema object or dict
            count: Number of examples to generate

        Returns:
            Single generated value if count=1, otherwise list of generated values

        Raises:
            TestGenerationError: If generation fails
        """
        schema_dict = None
        try:
            # Handle primitive types (int, str, float, bool)
            if isinstance(schema, type):
                type_map = {
                    int: {"type": "integer"},
                    str: {"type": "string"},
                    float: {"type": "number"},
                    bool: {"type": "boolean"},
                }
                schema_dict = type_map.get(schema, {"type": "string"})
            # Convert OpenAPI Schema to JSON Schema dict
            elif isinstance(schema, dict):
                schema_dict = schema
            else:
                schema_dict = schema.model_dump(exclude_none=True, by_alias=True)

            # If schema contains $ref, resolve it from spec
            if "$ref" in schema_dict:
                ref_path = schema_dict["$ref"]
                if ref_path.startswith("#/components/schemas/"):
                    schema_name = ref_path.split("/")[-1]
                    resolved_schema = self.introspector.get_schema(schema_name)
                    if isinstance(resolved_schema, dict):
                        schema_dict = resolved_schema
                    else:
                        schema_dict = resolved_schema.model_dump(
                            exclude_none=True, by_alias=True
                        )
                    logger.debug(f"Resolved $ref to schema: {schema_name}")

            # Use hypothesis-jsonschema to generate data
            strategy = from_schema(schema_dict)

            examples = []
            for _ in range(count):
                example = strategy.example()
                examples.append(example)

            logger.debug(f"Generated {count} examples from schema")

            # Return single value if count=1, otherwise return list
            return examples[0] if count == 1 else examples

        except Exception as e:
            raise TestGenerationError(
                f"Failed to generate test data: {e}",
                details={"schema": schema_dict, "error": str(e)},
            ) from e

    def generate_request_body(
        self,
        endpoint: EndpointInfo,
        media_type: str = "application/json",
        count: int = 1,
    ) -> list[Any]:
        """
        Generate request body examples for endpoint

        Args:
            endpoint: Endpoint metadata
            media_type: Media type (default: application/json)
            count: Number of examples

        Returns:
            List of generated request bodies

        Raises:
            TestGenerationError: If no request body or generation fails
        """
        if not endpoint.request_body:
            raise TestGenerationError(
                "Endpoint has no request body defined",
                details={"path": endpoint.path, "method": endpoint.method},
            )

        if (
            not endpoint.request_body.content
            or media_type not in endpoint.request_body.content
        ):
            available = (
                list(endpoint.request_body.content.keys())
                if endpoint.request_body.content
                else []
            )
            raise TestGenerationError(
                f"Media type not found in request body: {media_type}",
                details={
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "available_media_types": available,
                },
            )

        media = endpoint.request_body.content[media_type]
        # MediaType uses 'media_type_schema' field, not 'schema'
        schema = getattr(media, "media_type_schema", None) or getattr(
            media, "schema", None
        )
        if not schema:
            raise TestGenerationError(
                "Request body media type has no schema",
                details={
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "media_type": media_type,
                },
            )

        return self.generate_from_schema(schema, count=count)

    def generate_response_body(
        self,
        endpoint: Union[EndpointInfo, str],
        status_code: Union[str, None] = "200",
        media_type: str = "application/json",
        count: int = 1,
    ) -> list[Any]:
        """
        Generate response body examples for endpoint

        Args:
            endpoint: EndpointInfo object OR path string (if string, status_code is method)
            status_code: Response status code (default: "200") OR method string if endpoint is path
            media_type: Media type (default: application/json) OR status code if endpoint is path
            count: Number of examples

        Returns:
            List of generated response bodies

        Raises:
            TestGenerationError: If response not found or generation fails
        """
        # Handle both EndpointInfo object and path+method strings
        if isinstance(endpoint, str):
            # endpoint is path, status_code is method, media_type is status_code
            path = endpoint
            method = status_code
            actual_status_code = (
                media_type
                if isinstance(media_type, str) and media_type.isdigit()
                else "200"
            )
            media_type = "application/json"  # Reset to default
            endpoint_info = self.introspector.find_operation(path=path, method=method)
        else:
            endpoint_info = endpoint
            actual_status_code = status_code

        if actual_status_code not in endpoint_info.responses:
            available = list(endpoint_info.responses.keys())
            raise TestGenerationError(
                f"Status code not found in responses: {actual_status_code}",
                details={
                    "path": endpoint_info.path,
                    "method": endpoint_info.method,
                    "available_status_codes": available,
                },
            )

        response = endpoint_info.responses[actual_status_code]
        if not response.content or media_type not in response.content:
            available = list(response.content.keys()) if response.content else []
            raise TestGenerationError(
                f"Media type not found in response: {media_type}",
                details={
                    "path": endpoint_info.path,
                    "method": endpoint_info.method,
                    "status_code": actual_status_code,
                    "available_media_types": available,
                },
            )

        media = response.content[media_type]
        # MediaType uses 'media_type_schema' field, not 'schema'
        schema = getattr(media, "media_type_schema", None) or getattr(
            media, "schema", None
        )
        if not schema:
            raise TestGenerationError(
                "Response media type has no schema",
                details={
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "status_code": status_code,
                    "media_type": media_type,
                },
            )

        return self.generate_from_schema(schema, count=count)

    def generate_parameters(
        self,
        endpoint: Union[EndpointInfo, str],
        location: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate parameter values for endpoint

        Args:
            endpoint: EndpointInfo object OR path string (if string, location is method)
            location: Filter by parameter location (query, path, header, cookie) OR method string if endpoint is path

        Returns:
            Dict of parameter name -> generated value

        Raises:
            TestGenerationError: If generation fails
        """
        # Handle both EndpointInfo object and path+method strings
        if isinstance(endpoint, str):
            # endpoint is path, location is method
            path = endpoint
            method = location
            endpoint_info = self.introspector.find_operation(path=path, method=method)
            location = None  # Reset location since it was used for method
        else:
            endpoint_info = endpoint

        parameters = endpoint_info.parameters

        if location:
            parameters = [p for p in parameters if p.param_in == location]

        if not parameters:
            return {}

        result: dict[str, Any] = {}

        for param in parameters:
            # Parameter uses 'param_schema' field in openapi-pydantic
            schema = getattr(param, "param_schema", None)
            if not schema:
                logger.warning(f"Parameter {param.name} has no schema, skipping")
                continue

            try:
                # generate_from_schema returns single value when count=1
                value = self.generate_from_schema(schema, count=1)
                result[param.name] = value
            except Exception as e:
                logger.warning(
                    f"Failed to generate value for parameter {param.name}: {e}"
                )
                continue

        return result


__all__ = ["TestDataGenerator"]
