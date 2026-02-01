"""
Main OpenAPI client facade

This module provides the primary interface for working with OpenAPI specifications,
orchestrating parsing, validation, introspection, test generation, and HTTP calls.
"""

from pathlib import Path
from typing import Any

from common.logger.utils.helpers import get_logger
from common.openapi.config import DEFAULT_CONFIG, OpenAPIConfig
from common.openapi.generation import MockGenerator, TestDataGenerator
from common.openapi.http import DynamicHTTPClient
from common.openapi.introspection import EndpointInfo, SchemaInfo, SpecIntrospector
from common.openapi.models import OpenAPI, SpecDict
from common.openapi.parsing import SpecParser
from common.openapi.validation import SpecValidator

logger = get_logger(__name__)


class OpenAPIClient:
    """
    Unified client for OpenAPI specification operations

    This is the main entry point for working with OpenAPI specs. It provides:

    1. **Parsing**: Load and resolve specs from files/URLs
    2. **Introspection**: Query endpoints, schemas, parameters
    3. **Validation**: Validate requests/responses against spec
    4. **Test Generation**: Generate test data from schemas
    5. **HTTP Client**: Execute typed API calls

    Example:
        >>> from common.openapi import OpenAPIClient
        >>>
        >>> # Load spec
        >>> client = OpenAPIClient.from_file("openapi.yaml")
        >>>
        >>> # Introspect
        >>> endpoints = client.get_endpoints()
        >>> schemas = client.get_schemas()
        >>>
        >>> # Validate
        >>> client.validate_request("GET", "/users", query={"limit": 10})
        >>>
        >>> # Generate test data
        >>> test_data = client.generate_request_body("/users", "POST")
        >>>
        >>> # Execute HTTP calls
        >>> response = client.http.request("/users", "GET")
    """

    def __init__(
        self,
        spec_dict: SpecDict,
        spec_model: OpenAPI | None = None,
        config: OpenAPIConfig | None = None,
    ) -> None:
        """
        Initialize OpenAPI client

        Args:
            spec_dict: Resolved OpenAPI specification as dict
            spec_model: Optional pre-parsed Pydantic model
            config: Configuration for client behavior

        Note:
            Prefer using class methods `from_file()` or `from_url()` for construction
        """
        self.config = config or DEFAULT_CONFIG
        self.spec_dict = spec_dict

        # Lazy-load Pydantic model if not provided
        self._spec_model = spec_model
        self._parser: SpecParser | None = None
        self._introspector: SpecIntrospector | None = None
        self._validator: SpecValidator | None = None
        self._test_generator: TestDataGenerator | None = None
        self._mock_generator: MockGenerator | None = None
        self._http_client: DynamicHTTPClient | None = None

        logger.info(
            f"OpenAPIClient initialized: {self.spec_dict.get('info', {}).get('title', 'Unknown')}"
        )

    @classmethod
    def from_file(
        cls,
        file_path: str | Path,
        config: OpenAPIConfig | None = None,
    ) -> "OpenAPIClient":
        """
        Create client from local OpenAPI file

        Args:
            file_path: Path to OpenAPI specification (JSON or YAML)
            config: Configuration for client behavior

        Returns:
            Initialized OpenAPIClient

        Example:
            >>> client = OpenAPIClient.from_file("openapi.yaml")
        """
        config = config or DEFAULT_CONFIG
        parser = SpecParser(config)

        # Parse with $ref resolution
        spec_dict = parser.parse(file_path, resolve_refs=config.resolve_refs)

        # Optionally parse to Pydantic model
        spec_model = None
        if not config.lazy_load:
            spec_model = parser.parse_to_model(
                file_path, resolve_refs=config.resolve_refs
            )

        return cls(spec_dict=spec_dict, spec_model=spec_model, config=config)

    @classmethod
    def from_url(
        cls,
        url: str,
        config: OpenAPIConfig | None = None,
    ) -> "OpenAPIClient":
        """
        Create client from remote OpenAPI URL

        Args:
            url: URL to OpenAPI specification
            config: Configuration for client behavior

        Returns:
            Initialized OpenAPIClient

        Example:
            >>> client = OpenAPIClient.from_url("https://api.example.com/openapi.json")
        """
        config = config or DEFAULT_CONFIG
        parser = SpecParser(config)

        # Parse from URL (requires ref resolution)
        spec_dict = parser.parse(url, resolve_refs=True)

        spec_model = None
        if not config.lazy_load:
            spec_model = parser.parse_to_model(url, resolve_refs=True)

        return cls(spec_dict=spec_dict, spec_model=spec_model, config=config)

    @classmethod
    def from_dict(
        cls,
        spec_dict: SpecDict,
        config: OpenAPIConfig | None = None,
    ) -> "OpenAPIClient":
        """
        Create client from pre-loaded spec dict

        Args:
            spec_dict: OpenAPI specification as dict
            config: Configuration for client behavior

        Returns:
            Initialized OpenAPIClient

        Example:
            >>> spec = {"openapi": "3.0.0", ...}
            >>> client = OpenAPIClient.from_dict(spec)
        """
        return cls(spec_dict=spec_dict, spec_model=None, config=config)

    # === Properties (lazy-loaded sub-clients) ===

    @property
    def spec(self) -> OpenAPI:
        """Get parsed OpenAPI specification as Pydantic model"""
        if self._spec_model is None:
            logger.debug("Lazy-loading OpenAPI Pydantic model")
            # Convert 3.0 to 3.1 if needed
            spec_dict = self.spec_dict.copy()
            if spec_dict.get("openapi", "").startswith("3.0"):
                spec_dict["openapi"] = "3.1.0"
            self._spec_model = OpenAPI.model_validate(spec_dict)
        return self._spec_model

    @property
    def introspector(self) -> SpecIntrospector:
        """Get introspector for metadata extraction"""
        if self._introspector is None:
            self._introspector = SpecIntrospector(self.spec)
        return self._introspector

    @property
    def validator(self) -> SpecValidator:
        """Get validator for request/response validation"""
        if self._validator is None:
            self._validator = SpecValidator(self.spec_dict, self.config)
        return self._validator

    @property
    def test_generator(self) -> TestDataGenerator:
        """Get test data generator"""
        if self._test_generator is None:
            self._test_generator = TestDataGenerator(self.spec)
        return self._test_generator

    @property
    def mock_generator(self) -> MockGenerator:
        """Get mock data generator"""
        if self._mock_generator is None:
            self._mock_generator = MockGenerator(self.spec)
        return self._mock_generator

    @property
    def http(self) -> DynamicHTTPClient:
        """Get dynamic HTTP client"""
        if self._http_client is None:
            self._http_client = DynamicHTTPClient(self.spec, config=self.config)
        return self._http_client

    # === Convenience methods (delegate to sub-clients) ===

    # Introspection
    def get_endpoints(self, tags: list[str] | None = None) -> list[EndpointInfo]:
        """Get all endpoints (optionally filtered by tags)"""
        return self.introspector.get_endpoints(tags=tags)

    def find_operation(
        self,
        path: str | None = None,
        method: str | None = None,
        operation_id: str | None = None,
    ) -> EndpointInfo:
        """Find operation by path+method or operationId"""
        return self.introspector.find_operation(
            path=path, method=method, operation_id=operation_id
        )

    def get_schemas(self) -> dict[str, Any]:
        """Get all schema components"""
        return self.introspector.get_schemas()

    def get_schema_info(self, name: str) -> SchemaInfo:
        """Get detailed schema information"""
        return self.introspector.get_schema_info(name)

    def get_tags(self) -> list[str]:
        """Get all unique tags"""
        return self.introspector.get_tags()

    def get_spec_info(self) -> dict[str, Any]:
        """Get specification metadata summary"""
        return self.introspector.get_spec_info()

    # Validation
    def validate_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> Any:  # Returns RequestValidationResult
        """Validate HTTP request against spec"""
        return self.validator.validate_request(method, path, headers, query, body)

    def validate_response(
        self,
        method: str,
        path: str,
        status_code: int,
        headers: dict[str, str] | None = None,
        body: Any | None = None,
    ) -> Any:  # Returns ResponseValidationResult
        """Validate HTTP response against spec"""
        return self.validator.validate_response(
            method, path, status_code, headers, body
        )

    # Test Generation
    def generate_request_body(
        self,
        path: str,
        method: str,
        media_type: str = "application/json",
        count: int = 1,
    ) -> list[Any]:
        """Generate test request bodies for endpoint"""
        endpoint = self.find_operation(path=path, method=method)
        return self.test_generator.generate_request_body(endpoint, media_type, count)

    def generate_response_body(
        self,
        path: str,
        method: str,
        status_code: str = "200",
        media_type: str = "application/json",
        count: int = 1,
    ) -> list[Any]:
        """Generate test response bodies for endpoint"""
        endpoint = self.find_operation(path=path, method=method)
        return self.test_generator.generate_response_body(
            endpoint, status_code, media_type, count
        )

    def generate_parameters(
        self,
        path: str,
        method: str,
        location: str | None = None,
    ) -> dict[str, Any]:
        """Generate parameter values for endpoint"""
        endpoint = self.find_operation(path=path, method=method)
        return self.test_generator.generate_parameters(endpoint, location)

    # Mock Generation
    def generate_mock_response(
        self,
        path: str,
        method: str,
        status_code: str = "200",
        count: int = 1,
    ) -> Any:
        """Generate mock response for endpoint"""
        return self.mock_generator.generate_response(path, method, status_code, count)

    def generate_mock_request(self, path: str, method: str) -> dict[str, Any]:
        """Generate mock request body"""
        return self.mock_generator.generate_request(path, method)

    def generate_mock_parameters(self, path: str, method: str) -> dict[str, Any]:
        """Generate mock parameters"""
        return self.mock_generator.generate_parameters(path, method)

    # Utility
    def close(self) -> None:
        """Close HTTP client and release resources"""
        if self._http_client:
            self._http_client.close()
        logger.debug("OpenAPIClient closed")

    def __enter__(self) -> "OpenAPIClient":
        """Context manager entry"""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit"""
        self.close()

    def __repr__(self) -> str:
        """String representation"""
        info = self.spec_dict.get("info", {})
        title = info.get("title", "Unknown")
        version = info.get("version", "Unknown")
        return f"OpenAPIClient(title='{title}', version='{version}')"


__all__ = ["OpenAPIClient"]
