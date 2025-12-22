"""
Synchronous HTTP client with retry logic

This module provides a typed HTTP client that automatically
configures requests based on OpenAPI operation definitions.
"""

from typing import Any, Optional

import httpx

from common.logger.utils.helpers import get_logger
from common.openapi.config import OpenAPIConfig
from common.openapi.exceptions import HTTPClientError, OperationNotFoundError
from common.openapi.http.retry import with_http_retry
from common.openapi.introspection import SpecIntrospector
from common.openapi.models import OpenAPI

logger = get_logger(__name__)


class DynamicHTTPClient:
    """
    Dynamic HTTP client configured from OpenAPI spec with retry logic

    Features:
    - Automatic URL construction from base URL + path
    - Parameter injection (path, query, header)
    - Request body serialization
    - Automatic retry with exponential backoff
    - Timeout configuration
    """

    def __init__(
        self,
        spec: OpenAPI,
        base_url: Optional[str] = None,
        config: Optional[OpenAPIConfig] = None,
        enable_retry: bool = True,
    ) -> None:
        """
        Initialize dynamic HTTP client

        Args:
            spec: Parsed OpenAPI specification
            base_url: Base URL for requests (overrides spec servers)
            config: Client configuration
            enable_retry: Enable automatic retry with exponential backoff
        """
        from common.openapi.config import DEFAULT_CONFIG

        self.spec = spec
        self.introspector = SpecIntrospector(spec)
        self.config = config or DEFAULT_CONFIG
        self.enable_retry = enable_retry

        # Determine base URL
        self.base_url = base_url or self.introspector.get_base_url() or ""
        if self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")

        # Create httpx client
        self._client = httpx.Client(
            timeout=self.config.default_timeout,
            follow_redirects=True,
        )

        logger.debug(
            f"Initialized HTTP client with base URL: {self.base_url}, "
            f"retry={'enabled' if enable_retry else 'disabled'}"
        )

    def request(
        self,
        path: str,
        method: str,
        path_params: Optional[dict[str, Any]] = None,
        query_params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        body: Optional[Any] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute HTTP request based on OpenAPI operation

        Args:
            path: API path (e.g., "/users/{id}")
            method: HTTP method
            path_params: Path parameters
            query_params: Query parameters
            headers: Request headers
            body: Request body
            **kwargs: Additional httpx request options

        Returns:
            httpx Response object

        Raises:
            HTTPClientError: If request fails
            OperationNotFoundError: If operation not found in spec
        """
        try:
            # Validate operation exists
            self.introspector.find_operation(path=path, method=method)

            # Execute with retry if enabled
            if self.enable_retry:
                return self._request_with_retry(
                    path, method, path_params, query_params, headers, body, **kwargs
                )
            else:
                return self._execute_request(
                    path, method, path_params, query_params, headers, body, **kwargs
                )

        except OperationNotFoundError:
            raise
        except Exception as e:
            raise HTTPClientError(
                f"HTTP request failed: {e}",
                details={"path": path, "method": method, "error": str(e)},
            ) from e

    @with_http_retry(max_attempts=3)
    def _request_with_retry(
        self,
        path: str,
        method: str,
        path_params: Optional[dict[str, Any]],
        query_params: Optional[dict[str, Any]],
        headers: Optional[dict[str, str]],
        body: Optional[Any],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute request with retry logic"""
        return self._execute_request(
            path, method, path_params, query_params, headers, body, **kwargs
        )

    def _execute_request(
        self,
        path: str,
        method: str,
        path_params: Optional[dict[str, Any]],
        query_params: Optional[dict[str, Any]],
        headers: Optional[dict[str, str]],
        body: Optional[Any],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute HTTP request without retry"""
        # Build URL with path parameters
        url = self._build_url(path, path_params)

        # Prepare request
        request_kwargs: dict[str, Any] = {
            "method": method.upper(),
            "url": url,
            "params": query_params,
            "headers": headers,
        }

        # Add body if present
        if body is not None:
            request_kwargs["json"] = body

        # Merge additional kwargs
        request_kwargs.update(kwargs)

        logger.debug(f"Executing request: {method.upper()} {url}")

        # Execute request
        response = self._client.request(**request_kwargs)

        logger.debug(f"Request completed: {response.status_code}")

        return response

    def request_by_operation_id(
        self,
        operation_id: str,
        path_params: Optional[dict[str, Any]] = None,
        query_params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        body: Optional[Any] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute request by operation ID

        Args:
            operation_id: OpenAPI operation ID
            path_params: Path parameters
            query_params: Query parameters
            headers: Request headers
            body: Request body
            **kwargs: Additional httpx options

        Returns:
            httpx Response object

        Raises:
            HTTPClientError: If request fails
            OperationNotFoundError: If operation not found
        """
        endpoint = self.introspector.find_operation(operation_id=operation_id)

        return self.request(
            path=endpoint.path,
            method=endpoint.method,
            path_params=path_params,
            query_params=query_params,
            headers=headers,
            body=body,
            **kwargs,
        )

    def _build_url(
        self, path: str, path_params: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Build full URL with path parameter substitution

        Args:
            path: API path template
            path_params: Path parameters

        Returns:
            Full URL string
        """
        # Substitute path parameters
        if path_params:
            for key, value in path_params.items():
                placeholder = f"{{{key}}}"
                if placeholder in path:
                    path = path.replace(placeholder, str(value))

        return f"{self.base_url}{path}"

    def close(self) -> None:
        """Close HTTP client and release resources"""
        self._client.close()
        logger.debug("HTTP client closed")

    def __enter__(self) -> "DynamicHTTPClient":
        """Context manager entry"""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit"""
        self.close()


__all__ = ["DynamicHTTPClient"]
