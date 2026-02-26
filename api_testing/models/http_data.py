from dataclasses import dataclass, field
import json
from typing import Any, Dict, Optional
import requests


@dataclass
class RequestData:
    """
    Represents all data required to send a single HTTP request.

    Each request supports exactly one MIME type in the body payload.

    Attributes:
        endpoint_path (str): API endpoint path (e.g., "/users/{id}").
        http_method (str): HTTP method (e.g., "GET", "POST", "PUT", "DELETE").
        mime_type (str): The MIME type of the request body 
            (e.g., "application/json", "multipart/form-data", "application/xml").
        parameters (Dict[str, Any]): Path or query parameters.
        body (Any): The request body payload (depends on MIME type).
        headers (Optional[Dict[str, str]]): HTTP headers.
        cookies (Optional[Dict[str, str]]): Cookies to include in the request.
    """

    endpoint_path: str
    http_method: str
    mime_type: str = "application/json"
    parameters: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Any] = None
    headers: Optional[Dict[str, str]] = field(default_factory=dict)
    cookies: Optional[Dict[str, str]] = field(default_factory=dict)
    expected_code: str = "2xx" # 2xx,4xx
    # ----------------------------------------------------------------------
    # Helper methods for RequestExecutor
    # ----------------------------------------------------------------------
    def resolve_headers(self) -> Dict[str, str]:
        """Return headers with Content-Type ensured."""
        headers = dict(self.headers or {})
        headers.setdefault("Content-Type", self.mime_type)
        return headers

    def resolve_cookies(self) -> Dict[str, str]:
        """Return cookies safely as a dictionary."""
        return self.cookies or {}

    def __repr__(self) -> str:
        """Readable string representation for debugging."""
        return (
            f"RequestData(method={self.http_method!r}, path={self.endpoint_path!r}, "
            f"mime_type={self.mime_type!r}, params={list(self.parameters.keys())}, "
            f"body_type={type(self.body).__name__})"
        )



@dataclass
class ResponseData:
    """
    Represents a standardized HTTP response returned by the RequestExecutor.

    Attributes:
        status_code (int): HTTP status code of the response.
        headers (Dict[str, str]): Response headers.
        cookies (Dict[str, str]): Cookies returned by the server.
        mime_type (str): Content-Type of the response.
        body (Any): Raw response body as string or bytes.
        parsed (Optional[Any]): Parsed content if applicable (e.g., JSON dict).
    """

    status_code: int
    headers: Dict[str, str]
    cookies: Dict[str, str]
    mime_type: str
    body: Any
    parsed: Optional[Any] = None

    # ------------------------------------------------------------------
    # Factory constructor from requests.Response
    # ------------------------------------------------------------------
    @classmethod
    def from_requests(cls, response: requests.Response) -> "ResponseData":
        """Create a ResponseData instance from a requests.Response."""
        mime_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        body = response.content

        parsed = None
        if "application/json" in mime_type:
            try:
                parsed = response.json()
            except Exception:
                parsed = None
        elif "text/" in mime_type or mime_type in ("application/xml", "text/xml"):
            parsed = response.text

        return cls(
            status_code=response.status_code,
            headers=dict(response.headers),
            cookies=response.cookies.get_dict(),
            mime_type=mime_type,
            body=body,
            parsed=parsed,
        )

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def ok(self) -> bool:
        """True if the response status code is 2xx."""
        return 200 <= self.status_code < 300

    def json(self) -> Optional[Dict[str, Any]]:
        """Return parsed JSON body, if available."""
        if self.parsed and isinstance(self.parsed, dict):
            return self.parsed
        try:
            return json.loads(self.body)
        except Exception:
            return None

    def text(self) -> str:
        """Return response body as text."""
        return (
            self.body.decode("utf-8", errors="ignore")
            if isinstance(self.body, (bytes, bytearray))
            else str(self.body)
        )
