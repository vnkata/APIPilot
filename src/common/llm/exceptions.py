"""
LLM Client Exceptions

Custom exceptions for LLM operations with detailed error context.
"""

from typing import Any, Optional, Dict


class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    def __init__(
        self,
        message: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.provider = provider
        self.model = model
        self.request_id = request_id
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.provider:
            parts.append(f"provider={self.provider}")
        if self.model:
            parts.append(f"model={self.model}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return " | ".join(parts)


class LLMConnectionError(LLMError):
    """Raised when connection to LLM provider fails."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        *,
        timeout_seconds: Optional[float] = None,
        **kwargs,
    ):
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            message = f"{message} (timeout={timeout_seconds}s)"
        super().__init__(message, **kwargs)


class LLMRateLimitError(LLMError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: Optional[float] = None,
        **kwargs,
    ):
        self.retry_after = retry_after
        if retry_after:
            message = f"{message} (retry_after={retry_after}s)"
        super().__init__(message, **kwargs)


class LLMAuthenticationError(LLMError):
    """Raised when authentication fails."""

    pass


class LLMValidationError(LLMError):
    """Raised when response validation fails (structured output)."""

    def __init__(
        self,
        message: str,
        *,
        validation_errors: Optional[list] = None,
        raw_response: Optional[str] = None,
        **kwargs,
    ):
        self.validation_errors = validation_errors or []
        self.raw_response = raw_response
        super().__init__(message, **kwargs)


class LLMContentFilterError(LLMError):
    """Raised when content is filtered by safety systems."""

    def __init__(
        self,
        message: str = "Content filtered by safety system",
        *,
        filter_reason: Optional[str] = None,
        **kwargs,
    ):
        self.filter_reason = filter_reason
        if filter_reason:
            message = f"{message} (reason={filter_reason})"
        super().__init__(message, **kwargs)


class LLMContextLengthError(LLMError):
    """Raised when context length exceeds model limits."""

    def __init__(
        self,
        message: str = "Context length exceeded",
        *,
        max_tokens: Optional[int] = None,
        requested_tokens: Optional[int] = None,
        **kwargs,
    ):
        self.max_tokens = max_tokens
        self.requested_tokens = requested_tokens
        if max_tokens and requested_tokens:
            message = f"{message} (max={max_tokens}, requested={requested_tokens})"
        super().__init__(message, **kwargs)


class LLMToolCallError(LLMError):
    """Raised when tool/function calling fails."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        self.tool_name = tool_name
        self.tool_args = tool_args
        if tool_name:
            message = f"{message} (tool={tool_name})"
        super().__init__(message, **kwargs)


class LLMCacheError(LLMError):
    """Raised when cache operations fail."""

    pass


class LLMStreamError(LLMError):
    """Raised when streaming fails mid-stream."""

    def __init__(
        self,
        message: str = "Stream interrupted",
        *,
        partial_content: Optional[str] = None,
        **kwargs,
    ):
        self.partial_content = partial_content
        super().__init__(message, **kwargs)


__all__ = [
    "LLMError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMValidationError",
    "LLMContentFilterError",
    "LLMContextLengthError",
    "LLMToolCallError",
    "LLMCacheError",
    "LLMStreamError",
]
