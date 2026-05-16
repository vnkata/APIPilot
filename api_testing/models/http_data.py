"""
HTTP Data Models for API Testing

Defines structured request and response data classes used by the runtime.
"""

from dataclasses import dataclass, field, asdict
import json
from typing import Any, Dict, Optional, Union
import requests


@dataclass
class RequestData:
    """
    Represents request data for a single API call.

    This model stores endpoint metadata, headers, cookies, query/path parameters,
    and payload data ready to be dispatched by a request executor.
    """
    endpoint_path: str
    http_method: str
    uuid: Optional[str] = ""
    mime_type: str = "application/json"
    parameters: Dict[str, Any] = field(default_factory=dict)
    body: Optional[Any] = None
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    expected_code: str = "2xx"

    def __post_init__(self):
        if not self.endpoint_path or not isinstance(self.endpoint_path, str):
            raise ValueError("endpoint_path must be a non-empty string")
        # if self.http_method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        #     raise ValueError(f"Unsupported http_method '{self.http_method}'")

        self.http_method = self.http_method.upper()
        self.mime_type = self.mime_type.lower()

    def resolve_headers(self) -> Dict[str, str]:
        """Resolve headers with default Content-Type if not provided."""
        resolved = dict(self.headers or {})
        resolved.setdefault("Content-Type", self.mime_type)
        return resolved

    def resolve_cookies(self) -> Dict[str, str]:
        """Return cookies map (safe default empty dictionary)."""
        return dict(self.cookies or {})

    def to_dict(self) -> Dict[str, Any]:
        """Serialize request data to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestData":
        """Create RequestData from a dictionary."""
        if not isinstance(data, dict):
            raise ValueError("RequestData.from_dict expects a dict")

        return cls(
            endpoint_path=data.get("endpoint_path", ""),
            http_method=data.get("http_method", "GET"),
            mime_type=data.get("mime_type", "application/json"),
            parameters=data.get("parameters", {}),
            body=data.get("body"),
            headers=data.get("headers", {}),
            cookies=data.get("cookies", {}),
            expected_code=data.get("expected_code", "2xx"),
        )

    def __repr__(self) -> str:
        return (
            f"RequestData(method={self.http_method!r}, endpoint={self.endpoint_path!r}, "
            f"mime_type={self.mime_type!r}, params={len(self.parameters)}, body_type={type(self.body).__name__})"
        )


@dataclass
class ResponseData:
    """
    Represents a normalized response from an HTTP request.

    Includes status code, headers, cookies, raw body, and parsed payload.
    """

    status_code: int
    headers: Dict[str, str]
    cookies: Dict[str, str]
    mime_type: str
    body: Union[str, bytes, Any]
    parsed: Optional[Any] = None
    encoding: Optional[str] = None

    @classmethod
    def from_requests(cls, response: requests.Response) -> "ResponseData":
        """Create a ResponseData object from requests.Response."""
        if response is None:
            return cls(
                status_code=0,
                headers={},
                cookies={},
                mime_type="",
                body="",
                parsed=None,
                encoding=None,
            )

        mime_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        body = response.text if response.text is not None else response.content

        parsed = None
        if "application/json" in mime_type:
            try:
                parsed = response.json()
            except ValueError:
                parsed = body
        elif mime_type.startswith("text/") or mime_type in ("application/xml", "text/xml"):
            parsed = response.text
        return cls(
            status_code=response.status_code,
            headers=dict(response.headers),
            cookies=response.cookies.get_dict(),
            mime_type=mime_type,
            body=body,
            parsed=parsed,
            encoding=response.encoding,
        )

    @property
    def ok(self) -> bool:
        """True if status code is in 2xx range."""
        return 200 <= self.status_code < 300

    # def json(self) -> Optional[Dict[str, Any]]:
    #     """Parse and return JSON body if possible."""
    #     if isinstance(self.parsed, dict):
    #         return self.parsed

    #     if isinstance(self.body, (bytes, bytearray)):
    #         text = self.body.decode(self.encoding or "utf-8", errors="ignore")
    #     else:
    #         text = str(self.body) if self.body is not None else ""

    #     try:
    #         return json.loads(text)
    #     except (ValueError, TypeError):
    #         return None

    # def text(self) -> str:
    #     """Return body as string, decoding bytes if needed."""
    #     if isinstance(self.body, (bytes, bytearray)):
    #         return self.body.decode(self.encoding or "utf-8", errors="ignore")
    #     return str(self.body or "")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize response data to dict."""
        return asdict(self)

    def __repr__(self) -> str:
        return (
            f"ResponseData(status_code={self.status_code}, mime_type={self.mime_type!r}, "
            f"body_type={type(self.body).__name__}, parsed={isinstance(self.parsed, (dict, list))})"
        )

    def __str__(self) -> str:
        return f"ResponseData({self.status_code} {self.mime_type})"

