"""
OpenAPI client package - Enhanced with modular architecture

A production-grade OpenAPI client with:
- **NEW**: Swagger 2.0 → OpenAPI 3.x auto-conversion
- **NEW**: Async HTTP client (httpx.AsyncClient)
- **NEW**: Retry logic with exponential backoff (tenacity)
- **NEW**: Streaming parser for large specs (ijson)
- **NEW**: Schema data validation
- **NEW**: Schemathesis integration for API fuzzing
- **NEW**: LRU cache layer (in-memory L1 + file L2)
- Spec parsing with $ref resolution (Prance)
- Typed models (openapi-pydantic)
- Request/response validation (openapi-core)
- Introspection and metadata extraction
- Test data generation (hypothesis)
- Dynamic HTTP client (sync + async)

**Modular Structure:**
- `parsing/` - Spec parsing, Swagger conversion, caching
- `validation/` - Request/response validation, schema validation
- `introspection/` - Spec analysis and querying
- `generation/` - Test data generation, fuzzing
- `http/` - HTTP clients (sync/async), retry logic

Usage:
    >>> from common.openapi import OpenAPIClient
    >>>
    >>> # Load spec (auto-converts Swagger 2.0)
    >>> client = OpenAPIClient.from_file("openapi.yaml")
    >>>
    >>> # Introspect
    >>> endpoints = client.get_endpoints()
    >>> schema = client.get_schema_info("User")
    >>>
    >>> # Validate data against schema
    >>> from common.openapi.validation import SchemaValidator
    >>> validator = SchemaValidator(client.spec)
    >>> result = validator.validate_data("User", {"name": "Alice", "age": 30})
    >>>
    >>> # Generate test data
    >>> test_body = client.generate_request_body("/users", "POST")
    >>>
    >>> # Execute requests (sync)
    >>> response = client.http.request("/users", "GET")
    >>>
    >>> # Execute requests (async)
    >>> from common.openapi.http import AsyncDynamicHTTPClient
    >>> async with AsyncDynamicHTTPClient(client.spec) as http:
    ...     response = await http.request("/users", "GET")
    >>>
    >>> # API fuzzing
    >>> from common.openapi.generation import SchemaFuzzer
    >>> fuzzer = SchemaFuzzer("openapi.yaml")
    >>> for case in fuzzer.generate_cases("/users", "POST", count=10):
    ...     print(case.body)
"""

# Main client
from common.openapi.client import OpenAPIClient

# Configuration
from common.openapi.config import DEFAULT_CONFIG, OpenAPIConfig

# Exceptions
from common.openapi.exceptions import (
    HTTPClientError,
    OpenAPIError,
    OperationNotFoundError,
    RefResolutionError,
    RequestValidationError,
    ResponseValidationError,
    SchemaNotFoundError,
    SchemaValidationError,
    SpecLoadError,
    SpecParseError,
    SpecValidationError,
    TestGenerationError,
)

# Metadata models
from common.openapi.introspection import EndpointInfo, SchemaInfo, SpecIntrospector

# Type models (re-exports from openapi-pydantic)
from common.openapi.models import (
    Components,
    HTTPMethod,
    Info,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Reference,
    RequestBody,
    Response,
    Schema,
    SpecDict,
)

# NEW: Modular subpackages
# Parsing
from common.openapi.parsing import SpecParser

# Validation
from common.openapi.validation import SpecValidator
from common.openapi.validation.schema_validator import SchemaValidator, ValidationResult

# Generation
from common.openapi.generation import TestDataGenerator
from common.openapi.generation.fuzzer import SchemaFuzzer

# HTTP clients
from common.openapi.http import DynamicHTTPClient
from common.openapi.http.async_client import AsyncDynamicHTTPClient
from common.openapi.http.retry import with_http_retry, with_retry

# Extraction (Constraints)
from common.openapi.extraction import (
    ResponseConstraintsExtractor,
    RequestResponseExtractor,
    ConstraintCSVWriter,
    PropertyConstraint,
    EndpointConstraint,
)


__all__ = [
    # Main client
    "OpenAPIClient",
    # Configuration
    "OpenAPIConfig",
    "DEFAULT_CONFIG",
    # Exceptions
    "OpenAPIError",
    "SpecLoadError",
    "SpecParseError",
    "SpecValidationError",
    "RefResolutionError",
    "RequestValidationError",
    "ResponseValidationError",
    "SchemaNotFoundError",
    "SchemaValidationError",
    "HTTPClientError",
    "OperationNotFoundError",
    "TestGenerationError",
    # Parsing
    "SpecParser",
    # Validation
    "SpecValidator",
    "SchemaValidator",
    "ValidationResult",
    # Introspection
    "SpecIntrospector",
    "EndpointInfo",
    "SchemaInfo",
    # Generation
    "TestDataGenerator",
    "SchemaFuzzer",
    # HTTP
    "DynamicHTTPClient",
    "AsyncDynamicHTTPClient",
    "with_retry",
    "with_http_retry",
    # Extraction (Constraints)
    "ResponseConstraintsExtractor",
    "RequestResponseExtractor",
    "ConstraintCSVWriter",
    "PropertyConstraint",
    "EndpointConstraint",
    # Type models
    "OpenAPI",
    "Operation",
    "PathItem",
    "Parameter",
    "RequestBody",
    "Response",
    "Schema",
    "Reference",
    "Components",
    "Info",
    "HTTPMethod",
    "SpecDict",
]
