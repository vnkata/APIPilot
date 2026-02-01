"""
OpenAPI validation using openapi-core

This module provides request/response validation against OpenAPI specs
using the openapi-core library with OAS 3.0/3.1 support.
"""

import hashlib
import json
from typing import Any

from openapi_core import OpenAPI as OpenAPICoreApp
from openapi_core.validation.exceptions import ValidationError as CoreValidationError

from common.logger.utils.helpers import get_logger
from common.openapi.config import OpenAPIConfig
from common.openapi.exceptions import (
    RequestValidationError,
    ResponseValidationError,
    SpecValidationError,
)
from common.openapi.models import SpecDict
from common.openapi.validation.request_wrapper import RequestWrapper
from common.openapi.validation.validation_result import (
    RequestValidationResult,
    ResponseValidationResult,
)

logger = get_logger(__name__)


class SpecValidator:
    """
    Validate HTTP requests and responses against OpenAPI specification

    Uses openapi-core for runtime validation with support for:
    - Request validation (path, query, header, body)
    - Response validation (status, headers, body)
    - Format validators (date, uuid, email, etc.)
    - Media type encoding/decoding
    - Style deserialization
    """

    def __init__(self, spec_dict: SpecDict, config: OpenAPIConfig) -> None:
        """
        Initialize validator

        Args:
            spec_dict: Resolved OpenAPI spec as dict
            config: Configuration for validation behavior

        Raises:
            SpecValidationError: If spec is invalid
        """
        self.config = config
        self.spec_dict = spec_dict

        try:
            # Create openapi-core app from spec dict
            self._core_app = OpenAPICoreApp.from_dict(spec_dict)
            logger.debug("Initialized openapi-core validator")
        except Exception as e:
            raise SpecValidationError(
                f"Failed to initialize validator: {e}",
                details={"error": str(e)},
            ) from e

    def _cache_key(
        self,
        method: str,
        path: str,
        headers: dict | None = None,
        query: dict | None = None,
        body: Any | None = None,
    ) -> str:
        """
        Generate cache key for validation result

        Args:
            method: HTTP method
            path: Request path
            headers: Headers dict
            query: Query params dict
            body: Request/response body

        Returns:
            Hash string for cache key
        """
        # Create hashable representation
        key_parts = [
            method.upper(),
            path,
            json.dumps(headers or {}, sort_keys=True),
            json.dumps(query or {}, sort_keys=True),
            json.dumps(body, sort_keys=True, default=str) if body else "",
        ]

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def validate_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> RequestValidationResult:
        """
        Validate HTTP request against spec

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            headers: Request headers
            query: Query parameters
            body: Request body

        Returns:
            RequestValidationResult with validation status and parsed values

        Raises:
            RequestValidationError: If validation encounters unexpected error
        """

        try:
            # Create request-like object for openapi-core
            request = self._build_request(method, path, headers, query, body)

            # Validate using openapi-core
            result = self._core_app.unmarshal_request(request)

            logger.debug(f"Request validation passed: {method} {path}")

            return RequestValidationResult(
                valid=True,
                errors=[],
                path_params=(
                    dict(result.parameters.path)
                    if hasattr(result, "parameters")
                    else {}
                ),
                query_params=(
                    dict(result.parameters.query)
                    if hasattr(result, "parameters")
                    else {}
                ),
                headers=(
                    dict(result.parameters.header)
                    if hasattr(result, "parameters")
                    else {}
                ),
                body=result.body,
            )

        except CoreValidationError as e:
            logger.warning(f"Request validation failed: {method} {path} - {e}")
            return RequestValidationResult(
                valid=False,
                errors=[str(e)],
                path_params={},
                query_params={},
                headers={},
                body=None,
            )
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            raise RequestValidationError(
                f"Validation error: {e}",
                details={"method": method, "path": path, "error": str(e)},
            ) from e

    def validate_response(
        self,
        method: str,
        path: str,
        status_code: int,
        headers: dict[str, str] | None = None,
        body: Any | None = None,
    ) -> ResponseValidationResult:
        """
        Validate HTTP response against spec

        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            headers: Response headers
            body: Response body

        Returns:
            ResponseValidationResult with validation status and parsed values

        Raises:
            ResponseValidationError: If validation encounters unexpected error
        """

        try:
            # Create request/response objects for openapi-core
            request = self._build_request(method, path)
            response = self._build_response(status_code, headers, body)

            # Validate using openapi-core
            result = self._core_app.unmarshal_response(request, response)

            logger.debug(
                f"Response validation passed: {method} {path} -> {status_code}"
            )

            return ResponseValidationResult(
                valid=True,
                errors=[],
                headers=dict(result.headers) if hasattr(result, "headers") else {},
                data=result.data if hasattr(result, "data") else result.body,
            )

        except CoreValidationError as e:
            logger.warning(
                f"Response validation failed: {method} {path} -> {status_code} - {e}"
            )
            return ResponseValidationResult(
                valid=False,
                errors=[str(e)],
                headers={},
                data=None,
            )
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            raise ResponseValidationError(
                f"Validation error: {e}",
                details={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "error": str(e),
                },
            ) from e

    def _build_request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> RequestWrapper:
        """Build request object compatible with openapi-core"""
        return RequestWrapper(
            method=method,
            path=path,
            body=body,
            query=query,
            headers=headers,
            host_url="http://localhost",
            content_type=(
                headers.get("Content-Type", "application/json")
                if headers
                else "application/json"
            ),
        )

    def _build_response(
        self,
        status_code: int,
        headers: dict[str, str] | None = None,
        body: Any | None = None,
    ) -> Any:
        """Build response object compatible with openapi-core"""

        class SimpleResponse:
            def __init__(self, status_code: int, headers: dict, body: Any):
                self.status_code = status_code
                self.headers = headers or {}
                self.data = body

            @property
            def mimetype(self) -> str:
                return self.headers.get("Content-Type", "application/json")

        return SimpleResponse(status_code, headers or {}, body)

    def is_strict(self) -> bool:
        """Check if strict validation is enabled"""
        return self.config.strict_validation


__all__ = ["SpecValidator"]
