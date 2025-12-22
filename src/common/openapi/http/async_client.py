"""
Asynchronous HTTP client with retry logic

This module provides an async HTTP client that automatically
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


class AsyncDynamicHTTPClient:
    """
    Async dynamic HTTP client configured from OpenAPI spec with retry logic

    Features:
    - Asynchronous request execution
    - Automatic URL construction from base URL + path
    - Parameter injection (path, query, header)
    - Request body serialization
    - Automatic retry with exponential backoff
    - Timeout configuration
    - Context manager support (async with)
    """

    def __init__(
        self,
        spec: OpenAPI,
        base_url: Optional[str] = None,
        config: Optional[OpenAPIConfig] = None,
        enable_retry: bool = True,
    ) -> None:
        """
        Initialize async dynamic HTTP client

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

        # Create httpx async client
        self._client = httpx.AsyncClient(
            timeout=self.config.default_timeout,
            follow_redirects=True,
        )

        logger.debug(
            f"Initialized async HTTP client with base URL: {self.base_url}, "
            f"retry={'enabled' if enable_retry else 'disabled'}"
        )

    async def request(
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
        Execute async HTTP request based on OpenAPI operation

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
                return await self._request_with_retry(
                    path, method, path_params, query_params, headers, body, **kwargs
                )
            else:
                return await self._execute_request(
                    path, method, path_params, query_params, headers, body, **kwargs
                )

        except OperationNotFoundError:
            raise
        except Exception as e:
            raise HTTPClientError(
                f"Async HTTP request failed: {e}",
                details={"path": path, "method": method, "error": str(e)},
            ) from e

    @with_http_retry(max_attempts=3)
    async def _request_with_retry(
        self,
        path: str,
        method: str,
        path_params: Optional[dict[str, Any]],
        query_params: Optional[dict[str, Any]],
        headers: Optional[dict[str, str]],
        body: Optional[Any],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute async request with retry logic"""
        return await self._execute_request(
            path, method, path_params, query_params, headers, body, **kwargs
        )

    async def _execute_request(
        self,
        path: str,
        method: str,
        path_params: Optional[dict[str, Any]],
        query_params: Optional[dict[str, Any]],
        headers: Optional[dict[str, str]],
        body: Optional[Any],
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute async HTTP request without retry"""
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

        logger.debug(f"Executing async request: {method.upper()} {url}")

        # Execute async request
        response = await self._client.request(**request_kwargs)

        logger.debug(f"Async request completed: {response.status_code}")

        return response

    async def request_by_operation_id(
        self,
        operation_id: str,
        path_params: Optional[dict[str, Any]] = None,
        query_params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        body: Optional[Any] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute async request by operation ID

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

        return await self.request(
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

    async def aclose(self) -> None:
        """Close async HTTP client and release resources"""
        await self._client.aclose()
        logger.debug("Async HTTP client closed")

    async def __aenter__(self) -> "AsyncDynamicHTTPClient":
        """Async context manager entry"""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit"""
        await self.aclose()


__all__ = ["AsyncDynamicHTTPClient"]
