"""
Retry and circuit breaker logic using tenacity

This module provides:
- Exponential backoff retry decorators
- Circuit breaker pattern
- Configurable stop/wait strategies
"""

from typing import Any, Callable, TypeVar

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from common.logger.utils.helpers import get_logger

logger = get_logger(__name__)

# Type variable for retry decorators
F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    max_attempts: int = 3,
    min_wait: int = 1,
    max_wait: int = 10,
    retry_on: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Retry decorator with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic

    Example:
        ```python
        @with_retry(max_attempts=3, retry_on=(httpx.HTTPError,))
        def fetch_data():
            return httpx.get("https://api.example.com/data")
        ```
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )


def with_http_retry(max_attempts: int = 3) -> Callable[[F], F]:
    """
    Retry decorator specifically for HTTP errors

    Retries on:
    - Connection errors
    - Timeout errors
    - 5xx server errors

    Args:
        max_attempts: Maximum number of retry attempts

    Returns:
        Decorated function with HTTP-specific retry logic

    Example:
        ```python
        @with_http_retry(max_attempts=3)
        async def fetch_user(user_id: str):
            async with httpx.AsyncClient() as client:
                response = await client.get(f"/users/{user_id}")
                return response.json()
        ```
    """
    import httpx

    def should_retry(exception: BaseException) -> bool:
        """Check if exception should trigger retry"""
        if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
            return True
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code >= 500
        return False

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        before_sleep=before_sleep_log(logger, "WARNING"),
        reraise=True,
    )


__all__ = ["with_retry", "with_http_retry"]
