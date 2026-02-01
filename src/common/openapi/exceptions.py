"""
Custom exceptions for OpenAPI client operations
"""

import json
from typing import Any


class OpenAPIError(Exception):
    """Base exception for all OpenAPI-related errors"""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message

    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary format

        Returns:
            Dict with error details for structured logging/API responses

        Example:
            >>> try:
            ...     raise OpenAPIError("Invalid spec", {"line": 42})
            ... except OpenAPIError as e:
            ...     print(e.to_dict())
            {"error": "Invalid spec", "details": {"line": 42}, "type": "OpenAPIError"}
        """
        return {
            "error": self.message,
            "details": self.details,
            "type": self.__class__.__name__,
        }

    def to_json(self, indent: int | None = 2) -> str:
        """
        Convert exception to JSON string

        Args:
            indent: JSON indentation (default: 2)

        Returns:
            JSON string representation

        Example:
            >>> try:
            ...     raise OpenAPIError("Test error")
            ... except OpenAPIError as e:
            ...     print(e.to_json())
        """
        return json.dumps(self.to_dict(), indent=indent)


class SpecLoadError(OpenAPIError):
    """Failed to load OpenAPI specification from source"""

    pass


class SpecParseError(OpenAPIError):
    """Failed to parse OpenAPI specification (invalid format/structure)"""

    pass


class SpecValidationError(OpenAPIError):
    """OpenAPI specification is invalid according to OAS schema"""

    pass


class RefResolutionError(OpenAPIError):
    """Failed to resolve $ref references in specification"""

    pass


class RequestValidationError(OpenAPIError):
    """HTTP request does not match OpenAPI specification"""

    pass


class ResponseValidationError(OpenAPIError):
    """HTTP response does not match OpenAPI specification"""

    pass


class OperationNotFoundError(OpenAPIError):
    """Requested operation/path not found in specification"""

    def __init__(
        self,
        path: str,
        method: str,
        available_paths: list[str] | None = None,
    ) -> None:
        message = f"Operation not found: {method.upper()} {path}"
        details = {"path": path, "method": method.upper()}
        if available_paths:
            details["available_paths"] = available_paths
        super().__init__(message, details)
        self.path = path
        self.method = method


class SchemaNotFoundError(OpenAPIError):
    """Requested schema/component not found in specification"""

    def __init__(
        self, schema_name: str, available_schemas: list[str] | None = None
    ) -> None:
        message = f"Schema not found: {schema_name}"
        details = {"schema_name": schema_name}
        if available_schemas:
            details["available_schemas"] = available_schemas
        super().__init__(message, details)
        self.schema_name = schema_name


class SchemaValidationError(OpenAPIError):
    """Failed to validate data against schema"""

    pass


class TestGenerationError(OpenAPIError):
    """Failed to generate test data from schema"""

    pass


class HTTPClientError(OpenAPIError):
    """Failed to execute HTTP request via dynamic client"""

    pass


__all__ = [
    "OpenAPIError",
    "SpecLoadError",
    "SpecParseError",
    "SpecValidationError",
    "RefResolutionError",
    "RequestValidationError",
    "ResponseValidationError",
    "OperationNotFoundError",
    "SchemaNotFoundError",
    "SchemaValidationError",
    "TestGenerationError",
    "HTTPClientError",
]
