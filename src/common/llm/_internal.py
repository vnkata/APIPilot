"""
LLM Client Internal Helpers

Private utilities extracted from LLMClient for cleaner organization.
These are implementation details and should not be imported directly.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError
from openai.types.chat import ChatCompletion
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
    before_sleep_log,
)

from common.llm.models import (
    LLMResponse,
    TokenUsage,
    ToolCall,
    RetryConfig,
)
from common.llm.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMContentFilterError,
    LLMContextLengthError,
)
from common.logger.utils.helpers import get_logger

if TYPE_CHECKING:
    from common.llm.config import LLMConfig

logger = get_logger(__name__)


def generate_request_id() -> str:
    """Generate unique request ID for tracing."""
    return str(uuid.uuid4())


def build_headers(
    config: "LLMConfig",
    request_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> Dict[str, str]:
    """Build headers for API request."""
    headers = dict(config.default_headers)
    rid = request_id or generate_request_id()
    headers["X-Request-Id"] = rid
    headers["X-Client-Request-Id"] = rid
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def map_api_exception(
    error: APIError,
    provider: str,
    model: str,
    timeout: float,
) -> LLMError:
    """Map OpenAI SDK exceptions to our exception types."""
    request_id = getattr(error, "request_id", None)
    base_kwargs = {
        "provider": provider,
        "model": model,
        "request_id": request_id,
    }

    if isinstance(error, RateLimitError):
        retry_after = None
        if hasattr(error, "response") and error.response:
            retry_after = error.response.headers.get("retry-after")
        return LLMRateLimitError(
            str(error),
            retry_after=float(retry_after) if retry_after else None,
            **base_kwargs,
        )

    if isinstance(error, APITimeoutError):
        return LLMTimeoutError(
            str(error),
            timeout_seconds=timeout,
            **base_kwargs,
        )

    if isinstance(error, APIConnectionError):
        return LLMConnectionError(str(error), **base_kwargs)

    # Check for specific error codes
    if hasattr(error, "code"):
        if error.code == "context_length_exceeded":
            return LLMContextLengthError(str(error), **base_kwargs)
        if error.code == "content_filter":
            return LLMContentFilterError(str(error), **base_kwargs)
        if error.code in ("invalid_api_key", "authentication_error"):
            return LLMAuthenticationError(str(error), **base_kwargs)

    return LLMError(str(error), **base_kwargs)


def parse_completion_response(
    completion: ChatCompletion,
    request_id: Optional[str] = None,
) -> LLMResponse:
    """Parse ChatCompletion to LLMResponse."""
    choice = completion.choices[0]
    message = choice.message

    # Parse tool calls if present
    tool_calls = None
    if message.tool_calls:
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=tc.function.arguments,
            )
            for tc in message.tool_calls
        ]

    # Parse usage
    usage = TokenUsage()
    if completion.usage:
        usage = TokenUsage(
            prompt_tokens=completion.usage.prompt_tokens,
            completion_tokens=completion.usage.completion_tokens,
            total_tokens=completion.usage.total_tokens,
        )

    # Get raw response (handle mocks gracefully)
    raw_response = None
    if hasattr(completion, "model_dump"):
        try:
            raw = completion.model_dump()
            if isinstance(raw, dict):
                raw_response = raw
        except Exception:
            pass

    return LLMResponse(
        content=message.content or "",
        model=completion.model,
        usage=usage,
        finish_reason=choice.finish_reason,
        tool_calls=tool_calls,
        request_id=request_id or completion.id,
        raw_response=raw_response,
    )


def create_retry_decorator(
    config: Optional[RetryConfig] = None,
    max_retries: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
):
    """Create tenacity retry decorator with given settings."""
    if config:
        max_retries = config.max_retries
        min_wait = config.min_wait
        max_wait = config.max_wait

    return retry(
        retry=retry_if_exception_type(
            (
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
            )
        ),
        wait=wait_exponential_jitter(
            initial=min_wait,
            max=max_wait,
        ),
        stop=stop_after_attempt(max_retries + 1),
        before_sleep=before_sleep_log(logger, log_level=20),  # INFO
        reraise=True,
    )


def parse_json_response(content: str, request_id: Optional[str] = None) -> Any:
    """Parse JSON content from LLM response."""
    from common.llm.exceptions import LLMValidationError

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMValidationError(
            f"Failed to parse JSON response: {e}",
            raw_response=content,
            request_id=request_id,
        )


def build_api_params(
    model: str,
    messages: List[Dict[str, Any]],
    temperature: float,
    max_tokens: Optional[int] = None,
    stream: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Build API parameters dict."""
    params: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if max_tokens:
        params["max_tokens"] = max_tokens

    if stream:
        params["stream"] = True

    params.update(kwargs)
    return params


__all__ = [
    "generate_request_id",
    "build_headers",
    "map_api_exception",
    "parse_completion_response",
    "create_retry_decorator",
    "parse_json_response",
    "build_api_params",
]
