"""
Validation result dataclasses for request/response validation
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestValidationResult:
    """Result of request validation"""

    valid: bool
    """Whether the request is valid"""

    errors: list[str] = field(default_factory=list)
    """List of validation error messages"""

    path_params: dict[str, Any] = field(default_factory=dict)
    """Validated path parameters"""

    query_params: dict[str, Any] = field(default_factory=dict)
    """Validated query parameters"""

    headers: dict[str, str] = field(default_factory=dict)
    """Validated headers"""

    body: Any | None = None
    """Validated request body"""

    @property
    def is_valid(self) -> bool:
        """Alias for valid attribute"""
        return self.valid


@dataclass
class ResponseValidationResult:
    """Result of response validation"""

    valid: bool
    """Whether the response is valid"""

    errors: list[str] = field(default_factory=list)
    """List of validation error messages"""

    headers: dict[str, str] = field(default_factory=dict)
    """Validated response headers"""

    data: Any | None = None
    """Validated response body data"""

    @property
    def is_valid(self) -> bool:
        """Alias for valid attribute"""
        return self.valid
