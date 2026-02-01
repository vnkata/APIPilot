"""
LLM Client Helpers

Unified convenience API for common LLM operations.

Main API:
- ask(): Universal method for text/structured outputs with streaming support
- ask_batch(): Parallel batch processing with I/O concurrency
- set_default_config(): Global configuration for all ask() calls
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager
from typing import (
    Any,
    TypeVar,
    overload,
)

from pydantic import BaseModel

from common.llm.client import LLMClient
from common.llm.config import LLMConfig
from common.llm.models import StreamChunk
from common.logger.logger_interface import LoggerInterface, LogLevel
from common.logger.utils.helpers import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

# Global default configuration
_default_config: LLMConfig | None = None


def set_default_config(config: LLMConfig) -> None:
    """
    Set global default configuration for all ask() calls.

    Args:
        config: LLM configuration to use as default

    Example:
        >>> from common.llm import set_default_config, LLMConfig
        >>> set_default_config(LLMConfig(model="gpt-4", enable_cache=True))
        >>> result = await ask("Hello")  # Uses gpt-4 with cache
    """
    global _default_config
    _default_config = config
    logger.info(
        f"Global LLM config set: model={config.model}, provider={config.provider.value}"
    )


def get_default_config() -> LLMConfig | None:
    """Get current global default configuration."""
    return _default_config


def _resolve_log_level(
    func_param: LogLevel | None,
    config: LLMConfig | None,
    default: LogLevel = LogLevel.INFO,
) -> LogLevel:
    """
    Resolve log level with priority: func_param > config.log_level > default.

    Args:
        func_param: Log level from function parameter (highest priority)
        config: LLMConfig object (may contain log_level)
        default: Default log level (lowest priority)

    Returns:
        Resolved log level to use
    """
    if func_param is not None:
        return func_param
    if config and config.log_level is not None:
        return config.log_level
    return default


@contextmanager
def _with_log_level(
    logger_instance: LoggerInterface, level: LogLevel
) -> Generator[None, None, None]:
    """
    Context manager to temporarily change logger level, restore after context.

    Args:
        logger_instance: Logger instance to modify
        level: Log level to set temporarily

    Yields:
        None

    Example:
        >>> with _with_log_level(logger, LogLevel.DEBUG):
        ...     logger.debug("This will be shown")
        >>> logger.debug("This may be hidden if original level was higher")
    """
    original_console = logger_instance.get_console_level()
    original_file = logger_instance.get_file_level()

    logger_instance.set_console_level(level)
    if original_file:
        logger_instance.set_file_level(level)

    try:
        yield
    finally:
        logger_instance.set_console_level(original_console)
        if original_file:
            logger_instance.set_file_level(original_file)


# Type-safe overloads for ask()
@overload
async def ask(
    prompt: str,
    *,
    response_model: None = None,
    system: str | None = None,
    history: list[dict[str, str]] | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    enable_cache: bool | None = None,
    enable_tracing: bool | None = None,
    enable_langfuse: bool | None = None,
    config: LLMConfig | None = None,
    log_level: LogLevel | None = None,
    **kwargs,
) -> str:
    """Ask with text response."""
    ...


@overload
async def ask[T: BaseModel](
    prompt: str,
    *,
    response_model: type[T],
    system: str | None = None,
    history: list[dict[str, str]] | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    enable_cache: bool | None = None,
    enable_tracing: bool | None = None,
    enable_langfuse: bool | None = None,
    config: LLMConfig | None = None,
    log_level: LogLevel | None = None,
    **kwargs,
) -> T:
    """Ask with structured response."""
    ...


async def ask[T: BaseModel](
    prompt: str,
    *,
    response_model: type[T] | None = None,
    system: str | None = None,
    history: list[dict[str, str]] | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    enable_cache: bool | None = None,
    enable_tracing: bool | None = None,
    enable_langfuse: bool | None = None,
    config: LLMConfig | None = None,
    log_level: LogLevel | None = None,
    **kwargs,
) -> str | T:
    """
    Universal LLM ask method with type-safe overloads.

    Supports:
    - Plain text responses (default)
    - Structured outputs via Pydantic models
    - Multi-turn conversations via history
    - Full configuration control
    - Configurable log verbosity

    For streaming, use ask_stream() instead.

    Args:
        prompt: User message/question
        response_model: Pydantic model for structured output (uses Instructor)
        system: Optional system message
        history: Previous conversation messages for multi-turn context
        model: Model identifier (default: gpt-4o-mini)
        temperature: Sampling temperature 0.0-2.0 (default: 0.7)
        max_tokens: Maximum tokens in response
        enable_cache: Enable response caching (default: None, uses config value).
                      If None, uses config.enable_cache (defaults to False).
                      Explicit True/False overrides config.
        enable_tracing: Enable OpenTelemetry tracing (default: None, uses config value).
                        If None, uses config.enable_tracing (defaults to True).
                        Explicit True/False overrides config.
        enable_langfuse: Enable Langfuse observability (default: None, uses config value).
                         If None, uses config.enable_langfuse (defaults to True).
                         Explicit True/False overrides config.
        config: Full LLMConfig object for advanced control
        log_level: Log level for this operation (default: INFO).
                  Priority: log_level parameter > config.log_level > INFO.
                  Controls verbosity of logs in helpers.py module only.
        **kwargs: Additional parameters passed to client.chat()

    Returns:
        - str: Plain text response (when response_model=None)
        - T: Structured Pydantic model (when response_model is provided)

    Examples:
        # Plain text
        >>> answer = await ask("What is 2+2?")
        >>> print(answer)  # "4"

        # Structured output
        >>> class Person(BaseModel):
        ...     name: str
        ...     age: int
        >>> person = await ask("Extract: John is 30", response_model=Person)
        >>> print(person.name)  # "John"

        # Streaming - use ask_stream() instead
        >>> async for chunk in ask_stream("Tell a story"):
        ...     print(chunk.delta, end="")

        # With conversation history
        >>> history = [
        ...     {"role": "user", "content": "My name is Alice"},
        ...     {"role": "assistant", "content": "Hello Alice!"}
        ... ]
        >>> response = await ask("What's my name?", history=history)
        >>> print(response)  # "Your name is Alice"

        # Full control with config
        >>> cfg = LLMConfig(model="gpt-4", enable_cache=True, cache_ttl=3600)
        >>> result = await ask("Complex query", config=cfg)

        # Control log verbosity
        >>> from common.logger import LogLevel
        >>> # Show debug logs for this call
        >>> result = await ask("Debug this", log_level=LogLevel.DEBUG)
        >>> # Quiet mode - only warnings and errors
        >>> result = await ask("Quiet please", log_level=LogLevel.WARNING)
        >>> # Via config
        >>> cfg = LLMConfig(log_level=LogLevel.DEBUG)
        >>> result = await ask("Via config", config=cfg)
    """
    # Build configuration
    if config is None:
        config = _default_config or LLMConfig()

    # Resolve parameters: None → use config value, explicit → override
    effective_enable_cache = (
        enable_cache if enable_cache is not None else config.enable_cache
    )
    effective_enable_tracing = (
        enable_tracing if enable_tracing is not None else config.enable_tracing
    )
    effective_enable_langfuse = (
        enable_langfuse if enable_langfuse is not None else config.enable_langfuse
    )

    # Create config with resolved values
    config = LLMConfig(
        model=model,
        enable_cache=effective_enable_cache,
        enable_tracing=effective_enable_tracing,
        enable_langfuse=effective_enable_langfuse,
        default_temperature=temperature,
        default_max_tokens=max_tokens,
        **{
            k: v
            for k, v in config.model_dump().items()
            if k
            not in [
                "model",
                "enable_cache",
                "enable_tracing",
                "enable_langfuse",
                "default_temperature",
                "default_max_tokens",
            ]
        },
    )

    # Resolve log level (priority: func_param > config > default)
    resolved_log_level = _resolve_log_level(log_level, config, LogLevel.INFO)

    # Build message list
    messages: list[dict[str, Any]] = []

    # Add history if provided
    if history:
        messages.extend(history)

    # Add system message
    if system:
        # Insert at beginning if no history, or after any existing system message
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system})
        else:
            # Append to existing system message
            messages[0]["content"] += f"\n\n{system}"

    # Add user prompt
    messages.append({"role": "user", "content": prompt})

    # Apply log level temporarily for this call
    with _with_log_level(logger, resolved_log_level):
        # Non-streaming modes
        async with LLMClient(config) as client:
            # Structured output mode
            if response_model is not None:
                logger.debug(
                    f"Structured ask: model={response_model.__name__}, llm={model}"
                )
                result = await client.structured(messages, response_model, **kwargs)
                return result

            # Plain text mode
            logger.debug(f"Text ask: prompt_length={len(prompt)}, llm={model}")
            response = await client.chat(
                messages, temperature=temperature, max_tokens=max_tokens, **kwargs
            )
            return response.content


async def ask_stream(
    prompt: str,
    *,
    system: str | None = None,
    history: list[dict[str, str]] | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    enable_cache: bool | None = None,
    enable_tracing: bool | None = None,
    enable_langfuse: bool | None = None,
    config: LLMConfig | None = None,
    log_level: LogLevel | None = None,
    **kwargs,
) -> AsyncGenerator[StreamChunk, None]:
    """
    Stream LLM response token by token.

    Separate function for streaming to avoid coroutine complexity.
    Use this instead of ask(..., stream=True) for cleaner API.

    Args:
        prompt: User message/question
        system: Optional system message
        history: Previous conversation messages
        model: Model identifier (default: gpt-4o-mini)
        temperature: Sampling temperature 0.0-2.0 (default: 0.7)
        max_tokens: Maximum tokens in response
        enable_cache: Enable response caching (default: None, uses config value).
                      If None, uses config.enable_cache (defaults to False).
                      Explicit True/False overrides config.
        enable_tracing: Enable OpenTelemetry tracing (default: None, uses config value).
                        If None, uses config.enable_tracing (defaults to True).
                        Explicit True/False overrides config.
        enable_langfuse: Enable Langfuse observability (default: None, uses config value).
                         If None, uses config.enable_langfuse (defaults to True).
                         Explicit True/False overrides config.
        config: Full LLMConfig object for advanced control
        log_level: Log level for this operation (default: INFO).
                  Priority: log_level parameter > config.log_level > INFO.
                  Controls verbosity of logs in helpers.py module only.
        **kwargs: Additional parameters passed to client.stream()

    Yields:
        StreamChunk: Content deltas and accumulated content

    Example:
        >>> async for chunk in ask_stream("Tell me a story"):
        ...     print(chunk.delta, end="", flush=True)
        >>> print()  # Newline after stream

        >>> # With log level control
        >>> from common.logger import LogLevel
        >>> async for chunk in ask_stream("Debug stream", log_level=LogLevel.DEBUG):
        ...     print(chunk.delta, end="")
    """
    # Build configuration
    if config is None:
        config = _default_config or LLMConfig()

    # Resolve parameters: None → use config value, explicit → override
    effective_enable_cache = (
        enable_cache if enable_cache is not None else config.enable_cache
    )
    effective_enable_tracing = (
        enable_tracing if enable_tracing is not None else config.enable_tracing
    )
    effective_enable_langfuse = (
        enable_langfuse if enable_langfuse is not None else config.enable_langfuse
    )

    # Create config with resolved values
    config = LLMConfig(
        model=model,
        enable_cache=effective_enable_cache,
        enable_tracing=effective_enable_tracing,
        enable_langfuse=effective_enable_langfuse,
        default_temperature=temperature,
        default_max_tokens=max_tokens,
        **{
            k: v
            for k, v in config.model_dump().items()
            if k
            not in [
                "model",
                "enable_cache",
                "enable_tracing",
                "enable_langfuse",
                "default_temperature",
                "default_max_tokens",
            ]
        },
    )

    # Resolve log level (priority: func_param > config > default)
    resolved_log_level = _resolve_log_level(log_level, config, LogLevel.INFO)

    # Build message list
    messages: list[dict[str, Any]] = []

    if history:
        messages.extend(history)

    if system:
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": system})
        else:
            messages[0]["content"] += f"\n\n{system}"

    messages.append({"role": "user", "content": prompt})

    # Apply log level temporarily for this call
    with _with_log_level(logger, resolved_log_level):
        # Stream response
        async with LLMClient(config) as client:
            async for chunk in client.stream(
                messages, temperature=temperature, max_tokens=max_tokens, **kwargs
            ):
                yield chunk


async def ask_batch[T: BaseModel](
    prompts: list[str],
    *,
    response_model: type[T] | None = None,
    system: str | None = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    enable_cache: bool | None = None,
    enable_tracing: bool | None = None,
    enable_langfuse: bool | None = None,
    config: LLMConfig | None = None,
    log_level: LogLevel | None = None,
    **kwargs,
) -> list[str | T | Exception]:
    """
    Batch process multiple prompts concurrently with I/O parallelism.

    All prompts share the same configuration (system, model, temperature, etc.).
    Uses asyncio.gather() with return_exceptions=True for resilient batch processing.

    Args:
        prompts: List of user prompts to process
        response_model: Optional Pydantic model for structured outputs
        system: Shared system message for all prompts
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum tokens per response
        enable_cache: Enable response caching (default: None, uses config value).
                      If None, uses config.enable_cache (defaults to False).
                      Explicit True/False overrides config.
        enable_tracing: Enable OpenTelemetry tracing (default: None, uses config value).
                        If None, uses config.enable_tracing (defaults to True).
                        Explicit True/False overrides config.
        enable_langfuse: Enable Langfuse observability (default: None, uses config value).
                         If None, uses config.enable_langfuse (defaults to True).
                         Explicit True/False overrides config.
        config: Full LLMConfig for advanced control
        log_level: Log level for batch operations (default: INFO).
                  Priority: log_level parameter > config.log_level > INFO.
                  Controls verbosity of logs in helpers.py module only.
        **kwargs: Additional parameters for all requests

    Returns:
        List of results (str or T) or exceptions for failed requests.
        Check with isinstance(result, Exception) to handle errors.

    Example:
        >>> prompts = ["What is 2+2?", "What is 3+3?", "What is 4+4?"]
        >>> results = await ask_batch(prompts, model="gpt-4o-mini")
        >>> for i, result in enumerate(results):
        ...     if isinstance(result, Exception):
        ...         print(f"Error {i}: {result}")
        ...     else:
        ...         print(f"Result {i}: {result}")

        >>> # Structured batch
        >>> class Sentiment(BaseModel):
        ...     label: str
        ...     score: float
        >>> sentiments = await ask_batch(
        ...     ["I love this!", "I hate this!", "It's okay"],
        ...     response_model=Sentiment,
        ...     system="Classify sentiment"
        ... )

        >>> # With log level control
        >>> from common.logger import LogLevel
        >>> results = await ask_batch(prompts, log_level=LogLevel.DEBUG)
    """
    # Resolve log level (priority: func_param > config > default)
    resolved_log_level = _resolve_log_level(log_level, config, LogLevel.INFO)

    # Apply log level temporarily for batch operation
    with _with_log_level(logger, resolved_log_level):
        logger.info(
            f"Batch ask: {len(prompts)} prompts, model={model}, structured={response_model is not None}"
        )

        # Create tasks for all prompts
        tasks = [
            ask(
                prompt=prompt,
                response_model=response_model,
                system=system,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_cache=enable_cache,
                enable_tracing=enable_tracing,
                enable_langfuse=enable_langfuse,
                config=config,
                log_level=log_level,  # Pass log_level to each ask() call
                **kwargs,
            )
            for prompt in prompts
        ]

        # Execute concurrently with error collection
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log summary
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = len(results) - successes
        logger.info(f"Batch complete: {successes} successes, {failures} failures")

        return results


__all__ = [
    "ask",
    "ask_stream",
    "ask_batch",
    "set_default_config",
    "get_default_config",
]
