"""
Request wrapper for openapi-core validation

This module provides a Request protocol implementation
to enable request validation with openapi-core.
"""

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

try:
    from openapi_core.datatypes import RequestParameters, ImmutableMultiDict, Headers
except ImportError:
    # Fallback for older openapi-core versions
    @dataclass
    class RequestParameters:
        query: Mapping[str, Any] = field(default_factory=dict)
        header: Mapping[str, Any] = field(default_factory=dict)
        cookie: Mapping[str, Any] = field(default_factory=dict)
        path: Mapping[str, Any] = field(default_factory=dict)

        def __getitem__(self, location: str) -> Any:
            return getattr(self, location)

    class ImmutableMultiDict(dict):
        pass

    class Headers(dict):
        pass


class RequestWrapper:
    """
    Request protocol implementation for openapi-core

    Implements the full openapi-core Request protocol with all
    required properties and attributes.
    """

    def __init__(
        self,
        method: str,
        path: str,
        body: Optional[bytes] = None,
        query: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        cookies: Optional[Mapping[str, str]] = None,
        path_params: Optional[Mapping[str, Any]] = None,
        host_url: str = "http://localhost",
        content_type: str = "application/json",
    ) -> None:
        """
        Initialize request wrapper

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path (e.g., /api/v1/users)
            body: Request body as bytes (None if not provided)
            query: Query parameters mapping
            headers: Request headers mapping
            cookies: Request cookies mapping
            path_params: Path parameters mapping
            host_url: Base URL with scheme and host
            content_type: Content-Type header value
        """
        self._method = method.lower()
        self._path = path
        self._body = (
            body
            if isinstance(body, bytes)
            else (body.encode("utf-8") if body else None)
        )
        self._host_url = host_url
        self._content_type = content_type.lower()

        # Build RequestParameters
        query_dict = ImmutableMultiDict(query or {})
        headers_dict = Headers(headers or {})
        cookies_dict = ImmutableMultiDict(cookies or {})
        path_dict = dict(path_params or {})

        # Ensure content-type in headers
        if self._body is not None and "content-type" not in {
            k.lower() for k in headers_dict
        }:
            headers_dict["Content-Type"] = content_type

        self.parameters = RequestParameters(
            query=query_dict,
            header=headers_dict,
            cookie=cookies_dict,
            path=path_dict,
        )

    @property
    def method(self) -> str:
        """HTTP method (lowercase)"""
        return self._method

    @property
    def path(self) -> str:
        """Request path"""
        return self._path

    @property
    def body(self) -> Optional[bytes]:
        """Request body as bytes"""
        return self._body

    @property
    def content_type(self) -> str:
        """Content-Type (lowercase with parameters)"""
        return self._content_type

    @property
    def host_url(self) -> str:
        """Base URL with scheme and host"""
        parsed = urlparse(self._host_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def full_url_pattern(self) -> str:
        """Full URL pattern (host_url + path)"""
        return f"{self.host_url}{self._path}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequestWrapper":
        """
        Create RequestWrapper from dict

        Args:
            data: Dict with keys: method, path, body, query, headers, etc.

        Returns:
            RequestWrapper instance
        """
        body = data.get("body")
        if body is not None and not isinstance(body, bytes):
            import json

            body = (
                json.dumps(body).encode("utf-8")
                if isinstance(body, dict)
                else str(body).encode("utf-8")
            )

        return cls(
            method=data.get("method", "GET"),
            path=data["path"],
            body=body,
            query=data.get("query"),
            headers=data.get("headers"),
            cookies=data.get("cookies"),
            path_params=data.get("path_params"),
            host_url=data.get("host_url", "http://localhost"),
            content_type=data.get("content_type", "application/json"),
        )


# Type alias for compatibility
Request = RequestWrapper
