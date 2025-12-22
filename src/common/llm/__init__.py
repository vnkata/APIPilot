"""
LLM Client Module

Provider-agnostic async LLM client with OpenAI-compatible protocol.

Features:
- OpenAI-compatible (works with OpenAI, Azure, vLLM, Ollama, LiteLLM)
- Async-first with SSE streaming
- Structured outputs with Pydantic validation (Instructor)
- Tool/function calling
- Response caching (exact + semantic)
- OpenTelemetry + Langfuse observability
- Automatic retries with exponential backoff

Quick Start:
    >>> from common.llm import LLMClient, LLMConfig
    >>>
    >>> config = LLMConfig(model="gpt-4o-mini")
    >>> async with LLMClient(config) as client:
    ...     response = await client.chat([
    ...         {"role": "user", "content": "Hello!"}
    ...     ])
    ...     print(response.content)

Structured Output:
    >>> from pydantic import BaseModel
    >>>
    >>> class Person(BaseModel):
    ...     name: str
    ...     age: int
    >>>
    >>> person = await client.structured(
    ...     [{"role": "user", "content": "Extract: John is 30 years old"}],
    ...     response_model=Person,
    ... )
    >>> print(person.name, person.age)

Streaming:
    >>> async for chunk in client.stream([{"role": "user", "content": "Tell me a story"}]):
    ...     print(chunk.delta, end="", flush=True)

Tool Calling:
    >>> from common.llm import ToolDefinition
    >>>
    >>> tools = [ToolDefinition(name="get_weather", description="...", parameters={...})]
    >>> response = await client.chat(messages, tools=tools, tool_choice="auto")
    >>> if response.has_tool_calls:
    ...     for tool_call in response.tool_calls:
    ...         print(tool_call.name, tool_call.parse_arguments())
"""

# Core client
from common.llm.client import (
    LLMClient,
    quick_chat,
    INSTRUCTOR_AVAILABLE,
)

# Configuration
from common.llm.config import (
    LLMConfig,
    LLMProvider,
    ModelPresets,
)

# Types
from common.llm.models import (
    ChatMessage,
    MessageRole,
    ToolDefinition,
    ToolCall,
    TokenUsage,
    LLMResponse,
    StreamChunk,
    ResponseFormat,
    CompletionParams,
    RetryConfig,
    MessageList,
    normalize_messages,
)

# Exceptions
from common.llm.exceptions import (
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMValidationError,
    LLMContentFilterError,
    LLMContextLengthError,
    LLMToolCallError,
    LLMCacheError,
    LLMStreamError,
)

# Cache
from common.llm.cache import (
    LLMCache,
    CacheEntry,
    get_llm_cache,
    reset_llm_cache,
    EMBEDDINGS_AVAILABLE,
)

# Tracing
from common.llm.tracing import (
    LLMTracer,
    SpanContext,
    get_tracer,
    reset_tracer,
    OTEL_AVAILABLE,
    LANGFUSE_AVAILABLE,
)

# Helpers
from common.llm.helpers import (
    ask,
    ask_stream,
    ask_batch,
    set_default_config,
    get_default_config,
)

__all__ = [
    # Client
    "LLMClient",
    "quick_chat",
    "INSTRUCTOR_AVAILABLE",
    # Config
    "LLMConfig",
    "LLMProvider",
    "ModelPresets",
    # Types
    "ChatMessage",
    "MessageRole",
    "ToolDefinition",
    "ToolCall",
    "TokenUsage",
    "LLMResponse",
    "StreamChunk",
    "ResponseFormat",
    "CompletionParams",
    "RetryConfig",
    "MessageList",
    "normalize_messages",
    # Exceptions
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
    # Cache
    "LLMCache",
    "CacheEntry",
    "get_llm_cache",
    "reset_llm_cache",
    "EMBEDDINGS_AVAILABLE",
    # Tracing
    "LLMTracer",
    "SpanContext",
    "get_tracer",
    "reset_tracer",
    "OTEL_AVAILABLE",
    "LANGFUSE_AVAILABLE",
    # Helpers
    "ask",
    "ask_stream",
    "ask_batch",
    "set_default_config",
    "get_default_config",
]
