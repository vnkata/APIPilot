"""
LLM Client - Core Implementation

Provider-agnostic async LLM client built on OpenAI-compatible protocol.
Supports streaming, structured outputs, tool calling, caching, and observability.

API:
- chat() → LLMResponse (supports tools via params)
- stream() → AsyncGenerator[StreamChunk]
- structured() → T (Pydantic model)
"""

from __future__ import annotations

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

import httpx
from openai import AsyncOpenAI, APIError
from pydantic import BaseModel

from common.llm.config import LLMConfig
from common.llm.models import (
    CompletionParams,
    LLMResponse,
    MessageList,
    ResponseFormat,
    RetryConfig,
    StreamChunk,
    TokenUsage,
    ToolDefinition,
    normalize_messages,
)
from common.llm.exceptions import (
    LLMError,
    LLMStreamError,
    LLMValidationError,
)
from common.llm._internal import (
    generate_request_id,
    build_headers,
    map_api_exception,
    parse_completion_response,
    create_retry_decorator,
    build_api_params,
)
from common.llm.tracing import LLMTracer, get_tracer
from common.llm.cache import LLMCache, get_llm_cache
from common.logger.utils.helpers import get_logger, LogLevel

# Instructor for structured outputs (optional)
try:
    import instructor
    from instructor import Mode, AsyncInstructor

    INSTRUCTOR_AVAILABLE = True
except ImportError:
    INSTRUCTOR_AVAILABLE = False
    instructor = None  # type: ignore
    Mode = None  # type: ignore

logger = get_logger(__name__, level=LogLevel.DEBUG)

T = TypeVar("T", bound=BaseModel)


class _InstructorTracingHook:
    """
    Hook handler for Instructor to capture raw response and usage information.

    This hook captures the completion response before it's parsed into a Pydantic model,
    allowing us to extract usage information and other metadata for tracing.
    """

    def __init__(self):
        """Initialize hook handler with empty state."""
        self.raw_response = None
        self.usage: Optional[Dict[str, int]] = None
        self.model: Optional[str] = None
        self.validation_errors: List[str] = []
        self.retry_count = 0

    def handle_completion_response(self, response: Any) -> None:
        """
        Handle completion response event.

        Args:
            response: Raw OpenAI ChatCompletion response object
        """
        try:
            self.raw_response = response
            # Extract model name
            if hasattr(response, "model"):
                self.model = response.model
            elif isinstance(response, dict) and "model" in response:
                self.model = response["model"]

            # Extract usage information
            usage_obj = None
            if hasattr(response, "usage"):
                usage_obj = response.usage
            elif isinstance(response, dict) and "usage" in response:
                usage_obj = response["usage"]

            if usage_obj:
                if hasattr(usage_obj, "prompt_tokens"):
                    self.usage = {
                        "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage_obj, "completion_tokens", 0),
                        "total_tokens": getattr(usage_obj, "total_tokens", 0),
                    }
                elif isinstance(usage_obj, dict):
                    self.usage = {
                        "prompt_tokens": usage_obj.get("prompt_tokens", 0),
                        "completion_tokens": usage_obj.get("completion_tokens", 0),
                        "total_tokens": usage_obj.get("total_tokens", 0),
                    }
        except Exception as e:
            logger.debug(f"Failed to extract data from completion response: {e}")

    def handle_completion_error(self, error: Exception) -> None:
        """
        Handle completion error event.

        Args:
            error: Exception that occurred during completion
        """
        try:
            self.validation_errors.append(str(error))
        except Exception as e:
            logger.debug(f"Failed to handle completion error: {e}")

    def handle_parse_error(self, error: Exception) -> None:
        """
        Handle parse error event (validation failure).

        Args:
            error: Exception that occurred during parsing/validation
        """
        try:
            self.validation_errors.append(f"Parse error: {str(error)}")
            self.retry_count += 1
        except Exception as e:
            logger.debug(f"Failed to handle parse error: {e}")


class LLMClient:
    """
    Provider-agnostic async LLM client.

    Features:
    - OpenAI-compatible protocol (works with OpenAI, vLLM, Ollama, LiteLLM)
    - SSE streaming support
    - Structured outputs with Pydantic validation (via Instructor)
    - Tool/function calling (via params.tools)
    - Response caching (exact + semantic)
    - OpenTelemetry + Langfuse observability
    - Automatic retries with exponential backoff

    API Methods:
    - chat() → LLMResponse: Standard chat completion
    - stream() → AsyncGenerator[StreamChunk]: Streaming response
    - structured() → T: Pydantic model extraction

    Langfuse Observability:
        When enabled, automatically captures full LLM call details:
        - Input messages (prompts) - set at span start
        - Output responses - set after completion
        - Token usage - set after completion
        - Model name - set after completion
        - Metadata (provider, request_id, temperature, etc.)

        Example with Langfuse:
            >>> config = LLMConfig(
            ...     model="gpt-4o-mini",
            ...     enable_langfuse=True,
            ...     langfuse_public_key="your-key",  # Or use env vars
            ...     langfuse_secret_key="your-secret",
            ... )
            >>> async with LLMClient(config) as client:
            ...     response = await client.chat([
            ...         {"role": "user", "content": "Hello!"}
            ...     ])
            ...     # Check Langfuse UI to see the trace with full details

    Example:
        >>> config = LLMConfig(model="gpt-4o-mini")
        >>> async with LLMClient(config) as client:
        ...     response = await client.chat([
        ...         {"role": "user", "content": "Hello!"}
        ...     ])
        ...     print(response.content)
    """

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        *,
        tracer: Optional[LLMTracer] = None,
        cache: Optional[LLMCache] = None,
    ):
        """
        Initialize LLM client.

        Args:
            config: LLM configuration (uses defaults if None)
            tracer: Custom tracer instance (uses global if None)
            cache: Custom cache instance (uses global if None)
        """
        self.config = config or LLMConfig()
        self._tracer = tracer
        self._cache = cache
        self._client: Optional[AsyncOpenAI] = None
        self._instructor_client: Optional[Any] = None
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazy initialization of clients."""
        if self._initialized:
            return

        # Create HTTP client with timeout
        timeout = httpx.Timeout(self.config.timeout, connect=30.0)
        http_client = httpx.AsyncClient(timeout=timeout)

        # Create OpenAI client
        client_kwargs = self.config.to_client_kwargs()
        self._client = AsyncOpenAI(http_client=http_client, **client_kwargs)

        # Initialize Instructor if available
        if INSTRUCTOR_AVAILABLE and self._client:
            try:
                mode_map = {
                    "tool_call": Mode.TOOLS,
                    "json": Mode.JSON,
                    "md_json": Mode.MD_JSON,
                    "json_schema": Mode.JSON_SCHEMA,
                }
                mode = mode_map.get(self.config.instructor_mode, Mode.TOOLS)
                self._instructor_client: AsyncInstructor = instructor.from_openai(
                    self._client, mode=mode
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Instructor: {e}")

        # Initialize tracer
        if self._tracer is None and self.config.enable_tracing:
            self._tracer = get_tracer(
                enable_otel=self.config.enable_tracing,
                enable_langfuse=self.config.enable_langfuse,
                enable_httpx_instrumentation=self.config.enable_httpx_instrumentation,
                langfuse_public_key=self.config.langfuse_public_key,
                langfuse_secret_key=self.config.langfuse_secret_key,
                langfuse_host=self.config.langfuse_host,
                langfuse_connection_timeout=self.config.langfuse_connection_timeout,
                langfuse_enable_health_check=self.config.langfuse_enable_health_check,
            )

        # Initialize cache
        if self._cache is None and self.config.enable_cache:
            self._cache = get_llm_cache(
                ttl=self.config.cache_ttl,
                enable_semantic=self.config.semantic_cache,
                embedding_model=self.config.embedding_model,
                similarity_threshold=self.config.semantic_cache_threshold,
            )

        self._initialized = True
        logger.debug(
            f"LLM client initialized: provider={self.config.provider.value}, "
            f"model={self.config.model}"
        )

    async def chat(
        self,
        messages: MessageList,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        params: Optional[CompletionParams] = None,
        tools: Optional[List[ToolDefinition]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        response_format: Optional[ResponseFormat] = None,
        retry: Optional[RetryConfig] = None,
        request_id: Optional[str] = None,
        skip_cache: bool = False,
        **kwargs,
    ) -> LLMResponse:
        """
        Send chat completion request.

        Args:
            messages: List of chat messages (dict or ChatMessage)
            temperature: Override default temperature
            max_tokens: Override default max tokens
            params: Full completion parameters (overrides individual args)
            tools: Tool definitions for function calling
            tool_choice: "auto", "none", "required", or specific tool
            response_format: TEXT, JSON, or JSON_SCHEMA
            retry: Per-request retry configuration
            request_id: Custom request ID for tracing
            skip_cache: Skip cache lookup/storage
            **kwargs: Additional parameters passed to API

        Returns:
            LLMResponse with content and metadata
        """
        await self._ensure_initialized()
        assert self._client is not None

        normalized = normalize_messages(messages)
        request_id = request_id or generate_request_id()

        # Check cache (skip for tool calls)
        should_cache = not skip_cache and not tools
        if should_cache and self._cache:
            cached = self._cache.get(normalized, self.config.model)
            if cached:
                logger.debug(f"Cache hit for request {request_id}")
                return LLMResponse(
                    content=cached.response,
                    model=self.config.model,
                    usage=TokenUsage(**cached.usage),
                    cached=True,
                    cache_key=cached.key,
                    request_id=request_id,
                )

        # Build parameters
        temp = temperature or (
            params.temperature if params else self.config.default_temperature
        )
        api_params = build_api_params(
            model=self.config.model,
            messages=normalized,
            temperature=temp,
            max_tokens=max_tokens or self.config.default_max_tokens,
        )

        # Handle params object
        if params:
            api_params.update(params.to_api_params())

        # Handle individual tool arguments
        if tools:
            api_params["tools"] = [t.to_openai_dict() for t in tools]
            if tool_choice:
                api_params["tool_choice"] = tool_choice

        # Handle response format
        if response_format == ResponseFormat.JSON:
            api_params["response_format"] = {"type": "json_object"}

        api_params.update(kwargs)

        headers = build_headers(self.config, request_id)

        # Create retry decorator
        retry_config = retry or RetryConfig(
            max_retries=self.config.max_retries,
            min_wait=self.config.retry_min_wait,
            max_wait=self.config.retry_max_wait,
        )
        retry_decorator = create_retry_decorator(retry_config)

        @retry_decorator
        async def _do_request():
            return await self._client.chat.completions.create(
                **api_params,
                extra_headers=headers,
            )

        # Execute with tracing
        span_attrs = {
            "llm.model": self.config.model,
            "llm.provider": self.config.provider.value,
            "llm.request_id": request_id,
            "llm.temperature": api_params.get("temperature"),
        }

        try:
            if self._tracer:
                with self._tracer.span(
                    "llm.chat",
                    attributes=span_attrs,
                    input=normalized,
                    model=self.config.model,  # Pass model at creation time for cost calculation
                ) as span:
                    completion = await _do_request()
                    response = parse_completion_response(completion, request_id)
                    if span:
                        # Set OTEL attributes
                        span.set_attributes(
                            {
                                "llm.usage.prompt_tokens": response.usage.prompt_tokens,
                                "llm.usage.completion_tokens": response.usage.completion_tokens,
                                "llm.usage.total_tokens": response.usage.total_tokens,
                                "llm.finish_reason": response.finish_reason,
                            }
                        )
                        # Store Langfuse data (will be sent via finalize_llm_data())
                        if response.content:
                            span.set_llm_output(response.content)
                        span.set_llm_usage(
                            {
                                "prompt_tokens": response.usage.prompt_tokens,
                                "completion_tokens": response.usage.completion_tokens,
                                "total_tokens": response.usage.total_tokens,
                            }
                        )
                        # Finalize all LLM data in single update() call
                        span.finalize_llm_data()
            else:
                completion = await _do_request()
                response = parse_completion_response(completion, request_id)

            # Cache response (skip for tool calls)
            if should_cache and self._cache and response.content:
                self._cache.set(
                    normalized,
                    self.config.model,
                    response.content,
                    {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "completion_tokens": response.usage.completion_tokens,
                        "total_tokens": response.usage.total_tokens,
                    },
                )

            return response

        except APIError as e:
            raise map_api_exception(
                e, self.config.provider.value, self.config.model, self.config.timeout
            )

    async def stream(
        self,
        messages: MessageList,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        params: Optional[CompletionParams] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream chat completion response.

        Args:
            messages: List of chat messages
            temperature: Override default temperature
            max_tokens: Override default max tokens
            params: Full completion parameters
            request_id: Custom request ID for tracing
            **kwargs: Additional parameters passed to API

        Yields:
            StreamChunk with content deltas
        """
        await self._ensure_initialized()
        assert self._client is not None

        normalized = normalize_messages(messages)
        request_id = request_id or generate_request_id()

        # Build parameters
        temp = temperature or (
            params.temperature if params else self.config.default_temperature
        )
        api_params = build_api_params(
            model=self.config.model,
            messages=normalized,
            temperature=temp,
            max_tokens=max_tokens or self.config.default_max_tokens,
            stream=True,
        )

        if params:
            api_params.update(params.to_api_params())

        api_params.update(kwargs)

        # Include usage information in streaming response (required for usage in final chunk)
        if api_params.get("stream"):
            api_params["stream_options"] = {"include_usage": True}

        headers = build_headers(self.config, request_id)

        accumulated_content = ""
        chunk_index = 0
        final_usage = None

        # Setup tracing
        span_attrs = {
            "llm.model": self.config.model,
            "llm.provider": self.config.provider.value,
            "llm.request_id": request_id,
            "llm.temperature": api_params.get("temperature"),
        }

        # Use span context manager for proper cleanup
        if self._tracer:
            with self._tracer.span(
                "llm.stream",
                attributes=span_attrs,
                input=normalized,
                model=self.config.model,  # Pass model at creation time for cost calculation
            ) as span_context:
                try:
                    stream = await self._client.chat.completions.create(
                        **api_params,
                        extra_headers=headers,
                    )

                    async for chunk in stream:

                        if not chunk.choices:

                            # Check for usage in chunks without choices (OpenAI sends usage in final chunk)
                            if hasattr(chunk, "usage") and chunk.usage:
                                final_usage = {
                                    "prompt_tokens": chunk.usage.prompt_tokens or 0,
                                    "completion_tokens": chunk.usage.completion_tokens
                                    or 0,
                                    "total_tokens": chunk.usage.total_tokens or 0,
                                }

                            continue

                        # Check for usage info in chunk (usually in final chunk)
                        if hasattr(chunk, "usage") and chunk.usage:
                            final_usage = {
                                "prompt_tokens": chunk.usage.prompt_tokens or 0,
                                "completion_tokens": chunk.usage.completion_tokens or 0,
                                "total_tokens": chunk.usage.total_tokens or 0,
                            }

                        delta = chunk.choices[0].delta
                        content = delta.content or ""
                        accumulated_content += content

                        yield StreamChunk(
                            content=accumulated_content,
                            delta=content,
                            finish_reason=chunk.choices[0].finish_reason,
                            chunk_index=chunk_index,
                            request_id=request_id,
                        )
                        chunk_index += 1

                    # After stream completes successfully, finalize Langfuse data
                    if span_context:
                        if accumulated_content:
                            span_context.set_llm_output(accumulated_content)

                        if final_usage:
                            span_context.set_llm_usage(final_usage)

                        span_context.finalize_llm_data()

                except APIError as e:
                    # Set partial data before raising
                    if span_context:
                        try:
                            span_context.set_llm_output(accumulated_content or "")
                            if span_context._langfuse_generation:
                                span_context._langfuse_generation.update(
                                    status_message=str(e), level="ERROR"
                                )
                            span_context.finalize_llm_data()
                        except Exception:
                            pass
                    raise LLMStreamError(
                        f"Stream interrupted: {e}",
                        partial_content=accumulated_content,
                        provider=self.config.provider.value,
                        model=self.config.model,
                        request_id=request_id,
                    )
        else:
            # No tracer, just yield chunks
            stream = await self._client.chat.completions.create(
                **api_params,
                extra_headers=headers,
            )

            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                content = delta.content or ""
                accumulated_content += content

                yield StreamChunk(
                    content=accumulated_content,
                    delta=content,
                    finish_reason=chunk.choices[0].finish_reason,
                    chunk_index=chunk_index,
                    request_id=request_id,
                )
                chunk_index += 1

    async def structured(
        self,
        messages: MessageList,
        response_model: Type[T],
        *,
        max_retries: Optional[int] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ) -> T:
        """
        Get structured response validated against Pydantic model.

        Uses Instructor library for automatic validation and retries.
        Includes full tracing support for Langfuse/OpenTelemetry.

        Args:
            messages: List of chat messages
            response_model: Pydantic model class for response (required)
            max_retries: Override default retry count for validation
            request_id: Custom request ID
            **kwargs: Additional parameters

        Returns:
            Instance of response_model

        Raises:
            LLMValidationError: If validation fails after all retries
        """
        if not INSTRUCTOR_AVAILABLE or not self._instructor_client:
            raise LLMError(
                "Instructor not available. Install with: pip install instructor",
                provider=self.config.provider.value,
                model=self.config.model,
            )

        await self._ensure_initialized()

        normalized = normalize_messages(messages)
        request_id = request_id or generate_request_id()
        headers = build_headers(self.config, request_id)

        retries = (
            max_retries
            if max_retries is not None
            else self.config.instructor_max_retries
        )

        # Setup tracing hook to capture usage information
        hook = _InstructorTracingHook()

        # Setup tracing span attributes
        span_attrs = {
            "llm.model": self.config.model,
            "llm.provider": self.config.provider.value,
            "llm.request_id": request_id,
            "llm.response_model": response_model.__name__,
            "llm.structured_output": True,
            "llm.max_retries": retries,
        }

        # Register hooks temporarily to capture response data
        # Note: Instructor's on() method registers hooks globally, so we need to
        # be careful about cleanup. Each call creates its own hook instance to avoid
        # mixing data between concurrent calls.
        hooks_registered = False
        try:
            # Register completion response hook
            if hasattr(self._instructor_client, "on"):
                try:
                    # Register our handler
                    self._instructor_client.on(
                        "completion:response", hook.handle_completion_response
                    )

                    # Register error hooks
                    self._instructor_client.on(
                        "completion:error", hook.handle_completion_error
                    )

                    self._instructor_client.on("parse:error", hook.handle_parse_error)
                    hooks_registered = True
                    logger.debug(
                        "Instructor hooks registered for structured output tracing"
                    )
                except Exception as hook_error:
                    logger.debug(
                        f"Failed to register Instructor hooks: {hook_error}. "
                        "Tracing will continue without usage information."
                    )
        except Exception as e:
            logger.debug(f"Failed to check for Instructor hooks: {e}")

        try:
            # Execute with tracing
            if self._tracer:
                with self._tracer.span(
                    "llm.structured",
                    attributes=span_attrs,
                    input=normalized,
                    model=self.config.model,
                ) as span:
                    try:
                        result = await self._instructor_client.chat.completions.create(
                            model=self.config.model,
                            messages=normalized,
                            response_model=response_model,
                            max_retries=retries,
                            extra_headers=headers,
                            **kwargs,
                        )

                        # Extract and set tracing data
                        if span:
                            # Serialize Pydantic model to JSON for Langfuse output
                            try:
                                import json

                                # Use model_dump_json() for proper JSON serialization
                                output_json = result.model_dump_json(indent=2)
                                span.set_llm_output(output_json)
                            except Exception as e:
                                # Fallback to string representation
                                logger.debug(
                                    f"Failed to serialize model to JSON: {e}, using str()"
                                )
                                span.set_llm_output(str(result))

                            # Set usage information from captured hook data
                            if hook.usage:
                                span.set_llm_usage(hook.usage)
                                # Also set as OTEL attributes
                                span.set_attributes(
                                    {
                                        "llm.usage.prompt_tokens": hook.usage.get(
                                            "prompt_tokens", 0
                                        ),
                                        "llm.usage.completion_tokens": hook.usage.get(
                                            "completion_tokens", 0
                                        ),
                                        "llm.usage.total_tokens": hook.usage.get(
                                            "total_tokens", 0
                                        ),
                                    }
                                )

                            # Add validation metadata
                            if hook.validation_errors:
                                span.set_attribute(
                                    "llm.validation_errors", len(hook.validation_errors)
                                )
                                span.set_attribute(
                                    "llm.validation_retries", hook.retry_count
                                )

                            # Finalize all LLM data
                            span.finalize_llm_data()

                        return result

                    except Exception as e:
                        # Handle errors in tracing span
                        if span:
                            try:
                                error_msg = str(e)
                                if "validation" in error_msg.lower():
                                    span.set_attribute("llm.validation_failed", True)
                                    span.set_attribute(
                                        "llm.validation_errors",
                                        len(hook.validation_errors),
                                    )
                                span.record_exception(e)
                            except Exception:
                                pass
                        # Re-raise to be handled by outer exception handler
                        raise
            else:
                # No tracer, just make the call
                result = await self._instructor_client.chat.completions.create(
                    model=self.config.model,
                    messages=normalized,
                    response_model=response_model,
                    max_retries=retries,
                    extra_headers=headers,
                    **kwargs,
                )
                return result

        except Exception as e:

            # Map to appropriate exception type
            if "validation" in str(e).lower():
                raise LLMValidationError(
                    f"Structured output validation failed: {e}",
                    provider=self.config.provider.value,
                    model=self.config.model,
                    request_id=request_id,
                )
            raise LLMError(
                str(e),
                provider=self.config.provider.value,
                model=self.config.model,
                request_id=request_id,
            )
        finally:
            # Cleanup: Unregister hooks if possible
            # Note: Instructor's on() method doesn't have an off() method,
            # so we can't easily unregister. This is a limitation of Instructor's API.
            # The hooks will remain registered, but they check for hook instance,
            # so they should be safe for concurrent use.
            pass

    async def close(self) -> None:
        """Close client and cleanup resources."""
        if self._client:
            await self._client.close()
        if self._tracer:
            self._tracer.shutdown()
        self._initialized = False
        logger.debug("LLM client closed")

    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry."""
        await self._ensure_initialized()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        # Flush tracer to ensure all Langfuse data is sent before closing
        if self._tracer:
            try:
                self._tracer.flush()
            except Exception as e:
                logger.debug(f"Failed to flush tracer: {e}")
        await self.close()


# Convenience function for quick usage
async def quick_chat(
    prompt: str,
    *,
    model: str = "gpt-4o-mini",
    system: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Quick one-off chat completion.

    Args:
        prompt: User message
        model: Model to use
        system: Optional system message
        **kwargs: Additional parameters

    Returns:
        Response content string
    """
    messages: List[Dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    config = LLMConfig(model=model)
    async with LLMClient(config) as client:
        response = await client.chat(messages, **kwargs)
        return response.content


__all__ = [
    "LLMClient",
    "quick_chat",
    "INSTRUCTOR_AVAILABLE",
]
