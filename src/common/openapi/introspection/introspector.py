"""
OpenAPI specification introspection and metadata extraction

This module provides tools to traverse and extract information
from OpenAPI specs (endpoints, schemas, parameters, etc.)
"""

from dataclasses import dataclass
from typing import Any, Optional

from common.logger.utils.helpers import get_logger
from common.openapi.exceptions import OperationNotFoundError, SchemaNotFoundError
from common.openapi.models import (
    OpenAPI,
    Operation,
    Parameter,
    RequestBody,
    Response,
    Schema,
    is_reference,
)
from common.openapi.utils import normalize_method, normalize_path

logger = get_logger(__name__)


@dataclass(frozen=True)
class EndpointInfo:
    """Metadata about an API endpoint"""

    path: str
    method: str
    operation_id: Optional[str]
    summary: Optional[str]
    description: Optional[str]
    tags: list[str]
    parameters: list[Parameter]
    request_body: Optional[RequestBody]
    responses: dict[str, Response]
    deprecated: bool = False


@dataclass(frozen=True)
class SchemaInfo:
    """Metadata about a schema component"""

    name: str
    schema: Schema
    description: Optional[str]
    properties: dict[str, Schema]
    required: list[str]


class SpecIntrospector:
    """
    Introspect and extract metadata from OpenAPI specifications

    Provides methods to:
    - List all endpoints/operations
    - Find operations by path/method/operationId/tag
    - Extract schema information
    - Get parameter definitions
    """

    def __init__(self, spec: OpenAPI) -> None:
        """
        Initialize introspector

        Args:
            spec: Parsed OpenAPI specification model
        """
        self.spec = spec
        self._endpoint_cache: Optional[list[EndpointInfo]] = None

    def get_endpoints(self, tags: Optional[list[str]] = None) -> list[EndpointInfo]:
        """
        Get all endpoints in specification

        Args:
            tags: Optional filter by tags

        Returns:
            List of endpoint metadata
        """
        if self._endpoint_cache is None:
            self._endpoint_cache = self._extract_all_endpoints()

        if tags is None:
            return self._endpoint_cache

        # Filter by tags
        return [
            ep for ep in self._endpoint_cache if any(tag in ep.tags for tag in tags)
        ]

    def _extract_all_endpoints(self) -> list[EndpointInfo]:
        """Extract all endpoints from spec"""
        endpoints: list[EndpointInfo] = []

        if not self.spec.paths:
            logger.warning("Specification has no paths defined")
            return endpoints

        for path, path_item in self.spec.paths.items():
            if is_reference(path_item):
                logger.warning(f"Skipping path with unresolved $ref: {path}")
                continue

            # Extract operations for each HTTP method
            for method in [
                "get",
                "post",
                "put",
                "delete",
                "patch",
                "options",
                "head",
                "trace",
            ]:
                operation = getattr(path_item, method, None)
                if operation:
                    endpoints.append(self._build_endpoint_info(path, method, operation))

        logger.debug(f"Extracted {len(endpoints)} endpoints from spec")
        return endpoints

    def _build_endpoint_info(
        self, path: str, method: str, operation: Operation
    ) -> EndpointInfo:
        """Build EndpointInfo from operation"""
        return EndpointInfo(
            path=normalize_path(path),
            method=normalize_method(method),
            operation_id=operation.operationId,
            summary=operation.summary,
            description=operation.description,
            tags=operation.tags or [],
            parameters=operation.parameters or [],
            request_body=operation.requestBody,
            responses=operation.responses or {},
            deprecated=operation.deprecated or False,
        )

    def find_operation(
        self,
        path: Optional[str] = None,
        method: Optional[str] = None,
        operation_id: Optional[str] = None,
    ) -> EndpointInfo:
        """
        Find operation by path+method or operationId

        Args:
            path: API path (e.g., "/users/{id}")
            method: HTTP method (e.g., "get")
            operation_id: Operation ID from spec

        Returns:
            EndpointInfo for matching operation

        Raises:
            OperationNotFoundError: If operation not found
        """
        endpoints = self.get_endpoints()

        if operation_id:
            for ep in endpoints:
                if ep.operation_id == operation_id:
                    return ep
            raise OperationNotFoundError(
                path=operation_id,
                method="*",
                available_paths=[
                    ep.operation_id for ep in endpoints if ep.operation_id
                ],
            )

        if path and method:
            normalized_path = normalize_path(path)
            normalized_method = normalize_method(method)

            for ep in endpoints:
                if ep.path == normalized_path and ep.method == normalized_method:
                    return ep

            raise OperationNotFoundError(
                path=normalized_path,
                method=normalized_method,
                available_paths=[f"{ep.method.upper()} {ep.path}" for ep in endpoints],
            )

        raise ValueError("Must provide either operation_id or both path and method")

    def get_schemas(self) -> dict[str, Schema]:
        """
        Get all schema components

        Returns:
            Dict of schema name -> Schema
        """
        if not self.spec.components or not self.spec.components.schemas:
            logger.warning("Specification has no schema components")
            return {}

        schemas: dict[str, Schema] = {}
        for name, schema_or_ref in self.spec.components.schemas.items():
            if not is_reference(schema_or_ref):
                schemas[name] = schema_or_ref

        logger.debug(f"Found {len(schemas)} schemas in spec")
        return schemas

    def get_schema(self, name: str) -> Schema:
        """
        Get specific schema by name

        Args:
            name: Schema name (from #/components/schemas/{name})

        Returns:
            Schema object

        Raises:
            SchemaNotFoundError: If schema not found
        """
        schemas = self.get_schemas()
        if name not in schemas:
            raise SchemaNotFoundError(name, available_schemas=list(schemas.keys()))
        return schemas[name]

    def get_schema_info(self, name: str) -> SchemaInfo:
        """
        Get detailed schema information

        Args:
            name: Schema name

        Returns:
            SchemaInfo with metadata

        Raises:
            SchemaNotFoundError: If schema not found
        """
        schema = self.get_schema(name)

        properties: dict[str, Schema] = {}
        if schema.properties:
            for prop_name, prop_schema in schema.properties.items():
                if not is_reference(prop_schema):
                    properties[prop_name] = prop_schema

        return SchemaInfo(
            name=name,
            schema=schema,
            description=schema.description,
            properties=properties,
            required=schema.required or [],
        )

    def get_paths(self) -> list[str]:
        """
        Get all API paths

        Returns:
            List of path strings
        """
        if not self.spec.paths:
            return []
        return [normalize_path(p) for p in self.spec.paths.keys()]

    def get_operations_by_tag(self, tag: str) -> list[EndpointInfo]:
        """
        Get all operations with specific tag

        Args:
            tag: Tag name

        Returns:
            List of endpoints with this tag
        """
        return self.get_endpoints(tags=[tag])

    def get_tags(self) -> list[str]:
        """
        Get all unique tags used in spec

        Returns:
            List of tag names
        """
        tags: set[str] = set()
        for endpoint in self.get_endpoints():
            tags.update(endpoint.tags)
        return sorted(tags)

    def get_base_url(self) -> Optional[str]:
        """
        Get first server base URL

        Returns:
            Base URL string or None
        """
        if self.spec.servers and len(self.spec.servers) > 0:
            return self.spec.servers[0].url
        return None

    def get_spec_info(self) -> dict[str, Any]:
        """
        Get specification metadata summary

        Returns:
            Dict with title, version, description, etc.
        """
        return {
            "title": self.spec.info.title if self.spec.info else "Unknown",
            "version": self.spec.info.version if self.spec.info else "Unknown",
            "description": self.spec.info.description if self.spec.info else None,
            "openapi_version": self.spec.openapi,
            "base_url": self.get_base_url(),
            "total_endpoints": len(self.get_endpoints()),
            "total_schemas": len(self.get_schemas()),
            "tags": self.get_tags(),
        }

    # Alias methods for test compatibility
    def get_endpoint(self, path: str, method: str) -> Optional[EndpointInfo]:
        """Get single endpoint by path and method (alias for find_operation)"""
        try:
            return self.find_operation(path=path, method=method)
        except OperationNotFoundError:
            return None

    def list_schemas(self) -> list[str]:
        """List all schema names (alias for get_schemas().keys())"""
        return list(self.get_schemas().keys())

    def get_parameters(self, path: str, method: str) -> list[Parameter]:
        """Get parameters for specific endpoint"""
        try:
            endpoint = self.find_operation(path=path, method=method)
            return endpoint.parameters
        except OperationNotFoundError:
            return []

    def get_request_body_schema(self, path: str, method: str) -> Optional[dict]:
        """Get request body schema for endpoint"""
        try:
            endpoint = self.find_operation(path=path, method=method)
            if endpoint.request_body and endpoint.request_body.content:
                # Get first media type schema
                for media_type, media in endpoint.request_body.content.items():
                    if media.media_type_schema:
                        return media.media_type_schema.model_dump()
            return None
        except OperationNotFoundError:
            return None

    def get_response_schema(
        self, path: str, method: str, status_code: str
    ) -> Optional[dict]:
        """Get response schema for endpoint and status code"""
        try:
            endpoint = self.find_operation(path=path, method=method)
            response = endpoint.responses.get(status_code)
            if response and response.content:
                # Get first media type schema
                for media_type, media in response.content.items():
                    if media.media_type_schema:
                        return media.media_type_schema.model_dump()
            return None
        except OperationNotFoundError:
            return None

    def get_servers(self) -> list[str]:
        """Get list of server URLs"""
        if self.spec.servers:
            return [server.url for server in self.spec.servers]
        return []

    def get_security_schemes(self) -> list[str]:
        """Get list of security scheme names"""
        if self.spec.components and self.spec.components.securitySchemes:
            return list(self.spec.components.securitySchemes.keys())
        return []

    def get_operation_by_id(self, operation_id: str) -> Optional[EndpointInfo]:
        """Get operation by operationId (alias for find_operation)"""
        try:
            return self.find_operation(operation_id=operation_id)
        except OperationNotFoundError:
            return None


__all__ = ["SpecIntrospector", "EndpointInfo", "SchemaInfo"]
