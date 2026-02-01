"""
LLM Client Type Definitions

Pydantic-based models for LLM operations.
All models use strict mode and are frozen (immutable).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(str, Enum):
    """Chat message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"  # Legacy, prefer TOOL


class ChatMessage(BaseModel):
    """Represents a chat message."""

    model_config = ConfigDict(
        strict=True,
        frozen=True,
        use_enum_values=True,
    )

    role: MessageRole
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    def to_openai_dict(self) -> dict[str, Any]:
        """Convert to OpenAI-compatible dict format."""
        msg: dict[str, Any] = {
            "role": self.role if isinstance(self.role, str) else self.role.value,
            "content": self.content,
        }
        if self.name:
            msg["name"] = self.name
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        return msg

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        """Create from dict format."""
        role = data.get("role", "user")
        if isinstance(role, str):
            try:
                role = MessageRole(role)
            except ValueError:
                role = MessageRole.USER
        return cls(
            role=role,
            content=data.get("content", ""),
            name=data.get("name"),
            tool_call_id=data.get("tool_call_id"),
            tool_calls=data.get("tool_calls"),
        )


class ToolDefinition(BaseModel):
    """Defines a tool/function for function calling."""

    model_config = ConfigDict(strict=True, frozen=True)

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema - inherently dynamic
    strict: bool = False  # Enforce strict schema validation

    def to_openai_dict(self) -> dict[str, Any]:
        """Convert to OpenAI tools format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
                "strict": self.strict,
            },
        }


class ToolCall(BaseModel):
    """Represents a tool call from the model."""

    model_config = ConfigDict(strict=True, frozen=True)

    id: str
    name: str
    arguments: str  # JSON string

    def parse_arguments(self) -> dict[str, Any]:
        """Parse arguments JSON string to dict."""
        import json

        try:
            return json.loads(self.arguments)
        except json.JSONDecodeError:
            return {}


class TokenUsage(BaseModel):
    """Token usage statistics."""

    model_config = ConfigDict(strict=True, frozen=True)

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    # Optional detailed breakdown (if available)
    cached_tokens: int | None = None
    reasoning_tokens: int | None = None


class LLMResponse(BaseModel):
    """Standard response from LLM operations."""

    model_config = ConfigDict(strict=True, frozen=False)  # Allow mutation for cache

    content: str
    model: str
    usage: TokenUsage
    finish_reason: str | None = None
    tool_calls: list[ToolCall] | None = None
    request_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    # Raw response for debugging (dynamic JSON)
    raw_response: dict[str, Any] | None = None

    # Cache info
    cached: bool = False
    cache_key: str | None = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.tool_calls)


class StreamChunk(BaseModel):
    """Represents a chunk from streaming response."""

    model_config = ConfigDict(strict=True, frozen=True)

    content: str
    delta: str  # Just the new content in this chunk
    finish_reason: str | None = None
    tool_calls: list[dict[str, Any]] | None = None

    # Streaming metadata
    chunk_index: int = 0
    request_id: str | None = None


class ResponseFormat(str, Enum):
    """Response format options."""

    TEXT = "text"
    JSON = "json_object"
    JSON_SCHEMA = "json_schema"


class CompletionParams(BaseModel):
    """Parameters for completion requests."""

    model_config = ConfigDict(strict=True, frozen=True)

    temperature: float = 0.7
    top_p: float | None = None
    max_tokens: int | None = None
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: list[str] | None = None
    seed: int | None = None

    # Response format
    response_format: ResponseFormat | None = None
    json_schema: dict[str, Any] | None = None  # JSON Schema - dynamic

    # Tool calling
    tools: list[ToolDefinition] | None = None
    tool_choice: str | dict[str, Any] | None = None

    def to_api_params(self) -> dict[str, Any]:
        """Convert to API-compatible dict, excluding None values."""
        params: dict[str, Any] = {
            "temperature": self.temperature,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }

        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.stop:
            params["stop"] = self.stop
        if self.seed is not None:
            params["seed"] = self.seed

        # Response format
        if self.response_format == ResponseFormat.JSON:
            params["response_format"] = {"type": "json_object"}
        elif self.response_format == ResponseFormat.JSON_SCHEMA and self.json_schema:
            params["response_format"] = {
                "type": "json_schema",
                "json_schema": self.json_schema,
            }

        # Tools
        if self.tools:
            params["tools"] = [t.to_openai_dict() for t in self.tools]
            if self.tool_choice:
                params["tool_choice"] = self.tool_choice

        return params


class RetryConfig(BaseModel):
    """Per-request retry configuration."""

    model_config = ConfigDict(strict=True, frozen=True)

    max_retries: int = Field(default=3, ge=0)
    min_wait: float = Field(default=1.0, gt=0)
    max_wait: float = Field(default=30.0, gt=0)


# Type aliases for convenience
MessageList = list[ChatMessage | dict[str, Any]]
ToolChoice = Union[Literal["auto", "none", "required"], dict[str, Any]]


def normalize_messages(messages: MessageList) -> list[dict[str, Any]]:
    """Convert messages to OpenAI-compatible format."""
    result = []
    for msg in messages:
        if isinstance(msg, ChatMessage):
            result.append(msg.to_openai_dict())
        elif isinstance(msg, dict):
            result.append(msg)
        else:
            raise ValueError(f"Invalid message type: {type(msg)}")
    return result


__all__ = [
    "MessageRole",
    "ChatMessage",
    "ToolDefinition",
    "ToolCall",
    "TokenUsage",
    "LLMResponse",
    "StreamChunk",
    "ResponseFormat",
    "CompletionParams",
    "RetryConfig",
    "MessageList",
    "ToolChoice",
    "normalize_messages",
]
