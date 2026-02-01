"""
LLM Client Configuration

Pydantic-settings based configuration with environment variable support.
Supports multiple providers via OpenAI-compatible protocol.
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from common.logger.logger_interface import LogLevel


class LLMProvider(str, Enum):
    """Supported LLM providers (all OpenAI-compatible)."""

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    VLLM = "vllm"
    LITELLM = "litellm"
    CUSTOM = "custom"

    @property
    def default_base_url(self) -> str | None:
        """Get default base URL for provider."""
        urls = {
            LLMProvider.OPENAI: None,  # SDK default
            LLMProvider.OLLAMA: "http://localhost:11434/v1",
            LLMProvider.VLLM: "http://localhost:8000/v1",
            LLMProvider.LITELLM: "http://localhost:4000/v1",
        }
        return urls.get(self)


class LLMConfig(BaseSettings):
    """
    Configuration for LLM Client.

    Supports environment variables with LLM_ prefix.
    Example: LLM_MODEL=gpt-4o-mini, LLM_API_KEY=sk-xxx
    """

    model_config = SettingsConfigDict(
        # env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # Provider settings
    provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="LLM provider type",
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="Model identifier",
    )
    api_key: str | None = Field(
        default=None,
        description="API key (falls back to OPENAI_API_KEY env var)",
    )
    base_url: str | None = Field(
        default=None,
        description="Base URL for API (None uses provider default)",
    )

    # Azure-specific (optional)
    azure_endpoint: str | None = Field(
        default=None,
        description="Azure OpenAI endpoint URL",
    )
    azure_deployment: str | None = Field(
        default=None,
        description="Azure deployment name",
    )
    api_version: str | None = Field(
        default="2024-02-01",
        description="API version (Azure)",
    )

    # Request settings
    timeout: float = Field(
        default=60.0,
        ge=1.0,
        le=600.0,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts",
    )
    retry_min_wait: float = Field(
        default=1.0,
        ge=0.1,
        description="Minimum wait between retries (seconds)",
    )
    retry_max_wait: float = Field(
        default=60.0,
        ge=1.0,
        description="Maximum wait between retries (seconds)",
    )

    # Default completion params
    default_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for completions",
    )
    default_max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Default max tokens (None for model default)",
    )

    # Headers
    default_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Default headers for all requests",
    )
    organization: str | None = Field(
        default=None,
        description="OpenAI organization ID",
    )
    project: str | None = Field(
        default=None,
        description="OpenAI project ID",
    )

    # Observability
    enable_tracing: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing",
    )
    enable_httpx_instrumentation: bool = Field(
        default=False,
        description="Enable global HTTPX instrumentation for OpenTelemetry. "
        "WARNING: This instruments ALL httpx clients in the process, not just LLM calls. "
        "Can cause issues with other HTTP clients. Only enable if needed.",
    )
    enable_langfuse: bool = Field(
        default=True,
        description="Enable Langfuse observability for LLM operations. "
        "Captures prompts, responses, token usage, and metadata. "
        "See LLMTracer docstring for setup instructions.",
    )
    langfuse_public_key: str | None = Field(
        default=None,
        description="Langfuse public key. "
        "Can also be set via LANGFUSE_PUBLIC_KEY environment variable. "
        "Required if enable_langfuse=True.",
    )
    langfuse_secret_key: str | None = Field(
        default=None,
        description="Langfuse secret key. "
        "Can also be set via LANGFUSE_SECRET_KEY environment variable. "
        "Required if enable_langfuse=True.",
    )
    langfuse_host: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_BASE_URL", "LANGFUSE_HOST"),
        description="Langfuse host URL (for self-hosted). "
        "Can also be set via LANGFUSE_HOST environment variable. "
        "Defaults to http://localhost:3000 if not provided. "
        "Use https://cloud.langfuse.com for cloud-hosted Langfuse.",
    )
    langfuse_connection_timeout: float = Field(
        default=2.0,
        ge=0.1,
        le=30.0,
        description="Timeout in seconds for Langfuse connection health check. "
        "Used to determine if Langfuse is available before enabling OpenTelemetry. "
        "Lower values reduce startup delay but may cause false negatives.",
    )
    langfuse_enable_health_check: bool = Field(
        default=True,
        description="Enable health check endpoint test before OTLP endpoint test. "
        "If True, tests /api/public/health first, then falls back to OTLP endpoint. "
        "Helps detect Langfuse availability more accurately.",
    )

    # Caching
    enable_cache: bool = Field(
        default=False,
        description="Enable response caching",
    )
    cache_ttl: int = Field(
        default=3600,
        ge=0,
        description="Cache TTL in seconds (0 for no expiration)",
    )
    semantic_cache: bool = Field(
        default=False,
        description="Enable semantic (embedding-based) caching",
    )
    semantic_cache_threshold: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Similarity threshold for semantic cache hits",
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Model for semantic cache embeddings",
    )

    # Instructor settings
    instructor_mode: str = Field(
        default="tool_call",
        description="Instructor mode: tool_call, json, md_json, etc.",
    )
    instructor_max_retries: int = Field(
        default=3,
        ge=0,
        description="Max retries for instructor validation",
    )

    # Logging
    log_level: LogLevel | None = Field(
        default=None,
        description="Log level for LLM operations (None uses default INFO). "
        "Can be overridden by log_level parameter in ask() functions.",
    )

    @field_validator("base_url", mode="before")
    @classmethod
    def resolve_base_url(cls, v: str | None, info) -> str | None:
        """Resolve base URL from provider if not explicitly set."""
        if v:
            return v.rstrip("/")
        return v

    @model_validator(mode="after")
    def validate_config(self) -> "LLMConfig":
        """Validate configuration after all fields are set."""
        # Set default base_url from provider if not specified
        if not self.base_url and self.provider.default_base_url:
            object.__setattr__(self, "base_url", self.provider.default_base_url)

        # Azure requires specific fields
        if self.provider == LLMProvider.AZURE_OPENAI:
            if not self.azure_endpoint:
                raise ValueError("azure_endpoint required for Azure OpenAI")

        # Langfuse validation - warn only, don't fail
        # This allows env vars to provide credentials at runtime
        if self.enable_langfuse:
            import os

            has_public_key = self.langfuse_public_key or os.getenv(
                "LANGFUSE_PUBLIC_KEY"
            )
            has_secret_key = self.langfuse_secret_key or os.getenv(
                "LANGFUSE_SECRET_KEY"
            )
            if not has_public_key or not has_secret_key:
                # Just warn, don't fail - allow env vars to provide these
                # This is logged at warning level in LLMTracer.__init__ as well
                pass

        return self

    def get_effective_base_url(self) -> str | None:
        """Get the effective base URL considering provider defaults."""
        return self.base_url or self.provider.default_base_url

    def to_client_kwargs(self) -> dict[str, Any]:
        """Convert config to kwargs for AsyncOpenAI client."""
        import os

        kwargs: dict[str, Any] = {
            "api_key": self.api_key or os.getenv("OPENAI_API_KEY"),
            "timeout": self.timeout,
            "max_retries": 0,  # We handle retries with tenacity
        }

        if self.base_url:
            kwargs["base_url"] = self.base_url
        if self.organization:
            kwargs["organization"] = self.organization
        if self.project:
            kwargs["project"] = self.project

        # Azure-specific
        if self.provider == LLMProvider.AZURE_OPENAI:
            kwargs["azure_endpoint"] = self.azure_endpoint
            kwargs["api_version"] = self.api_version
            if self.azure_deployment:
                kwargs["azure_deployment"] = self.azure_deployment

        return kwargs


class ModelPresets:
    """Preset configurations for common models."""

    @staticmethod
    def gpt4o() -> LLMConfig:
        """GPT-4o configuration."""
        return LLMConfig(model="gpt-4o", default_temperature=0.7)

    @staticmethod
    def gpt4o_mini() -> LLMConfig:
        """GPT-4o-mini configuration (cost-effective)."""
        return LLMConfig(model="gpt-4o-mini", default_temperature=0.7)

    @staticmethod
    def gpt4_turbo() -> LLMConfig:
        """GPT-4 Turbo configuration."""
        return LLMConfig(model="gpt-4-turbo", default_temperature=0.7)

    @staticmethod
    def ollama_llama3(base_url: str = "http://localhost:11434/v1") -> LLMConfig:
        """Local Ollama with Llama 3."""
        return LLMConfig(
            provider=LLMProvider.OLLAMA,
            model="llama3.2",
            base_url=base_url,
            api_key="ollama",  # Ollama requires a dummy key
        )

    @staticmethod
    def vllm(model: str, base_url: str = "http://localhost:8000/v1") -> LLMConfig:
        """vLLM server configuration."""
        return LLMConfig(
            provider=LLMProvider.VLLM,
            model=model,
            base_url=base_url,
            api_key="EMPTY",  # vLLM often doesn't require auth
        )


__all__ = [
    "LLMProvider",
    "LLMConfig",
    "ModelPresets",
]
