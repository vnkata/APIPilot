"""
OpenAI Model implementation using common.llm infrastructure.

Uses common.llm.ask() for LLM calls and StructuredOutputExtractor for structured outputs.
"""

import asyncio
import re

from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from api_testing.models.base_model import APITestingBaseLLMModel
from common.llm import ask
from common.llm.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from common.llm.extractors import ExtractionError, StructuredOutputExtractor
from common.logger import LogLevel, get_logger

logger = get_logger("openai_model", level=LogLevel.DEBUG)

# Default model if none specified
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def _sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """Sanitize text for safe logging (remove potential secrets, limit length).

    Args:
        text: Text to sanitize
        max_length: Maximum length to log

    Returns:
        Sanitized text
    """
    # Remove potential API keys/tokens (common patterns)
    sanitized = re.sub(
        r"(api[_-]?key|token|bearer)\s*[:=]\s*[\w\-]+",
        "[REDACTED]",
        text,
        flags=re.IGNORECASE,
    )

    # Truncate
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


class OpenAIModel(APITestingBaseLLMModel):
    """OpenAI Model implementation using common.llm.ask().

    Features:
    - Reuses common.llm infrastructure (no duplicate HTTP client)
    - Automatic retry on transient errors (rate limits, timeouts, network)
    - Structured output extraction via StructuredOutputExtractor
    - Sanitized debug logging (prevents secret leakage)

    Args:
        model: Model name (default: gpt-4o-mini)
        temperature: Sampling temperature 0.0-2.0 (default: 0.7)
        max_retries: Maximum retry attempts for transient errors (default: 3)
        **kwargs: Additional arguments (ignored for compatibility)

    Example:
        >>> model = OpenAIModel(model="gpt-4", temperature=0.1)
        >>> result = await model.a_generate(
        ...     prompt="Explain quantum computing",
        ...     system_prompt="You are a physics teacher"
        ... )
        >>> print(result)  # String response
        >>>
        >>> # Structured output
        >>> from pydantic import BaseModel
        >>> class Answer(BaseModel):
        ...     summary: str
        ...     details: list[str]
        >>>
        >>> result = await model.a_generate(
        ...     prompt="Explain quantum computing",
        ...     schema=Answer
        ... )
        >>> print(result.summary)  # Pydantic model instance
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        **kwargs,
    ):
        """Initialize OpenAI model.

        Args:
            model: Model identifier (default: gpt-4o-mini)
            temperature: Sampling temperature (default: 0.7)
            max_retries: Retry attempts for transient errors (default: 3)
            **kwargs: Additional arguments (ignored)
        """
        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")

        self.temperature = temperature
        self.max_retries = max_retries

        model_name = model or DEFAULT_OPENAI_MODEL

        logger.debug(
            f"Initializing OpenAIModel: model={model_name}, "
            f"temperature={temperature}, max_retries={max_retries}"
        )

        super().__init__(model_name)

    def load_model(self, *args, **kwargs):
        """No-op: common.llm.ask() handles client instantiation.

        Returns:
            None (model is not pre-loaded)
        """
        return None

    def generate(
        self,
        prompt: str | list,
        schema: BaseModel | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str | dict | BaseModel:
        """Synchronous wrapper for a_generate().

        Args:
            prompt: User prompt (string or message list)
            schema: Pydantic model for structured output
            system_prompt: System instruction
            **kwargs: Override temperature, max_tokens, etc.

        Returns:
            String if no schema, otherwise Dict or BaseModel instance
        """
        return asyncio.run(self.a_generate(prompt, schema, system_prompt, **kwargs))

    @retry(
        retry=retry_if_exception_type(
            (LLMRateLimitError, LLMTimeoutError, LLMConnectionError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def a_generate(
        self,
        prompt: str | list,
        schema: BaseModel | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str | dict | BaseModel:
        """Generate LLM response using common.llm.ask().

        Flow:
        1. Call ask() to get raw text response
        2. If schema provided → extract structured output via StructuredOutputExtractor
        3. If no schema → return raw text

        Automatic retry on:
        - Rate limit errors (429)
        - Timeout errors
        - Connection errors (503, network issues)

        Fail fast on:
        - Authentication errors (401)
        - Invalid input errors (400)
        - Content filter errors

        Args:
            prompt: User prompt (string or message list)
            schema: Pydantic model for structured output
            system_prompt: System instruction
            **kwargs: Override temperature, max_tokens, enable_cache, etc.

        Returns:
            String if no schema, otherwise Dict or BaseModel instance

        Raises:
            LLMError: On non-retryable errors or after max retries
        """
        # Extract override parameters
        temperature = kwargs.get("temperature", self.temperature)
        max_tokens = kwargs.get("max_tokens", None)
        enable_cache = kwargs.get("enable_cache", None)

        # Convert prompt to string if it's a list (message format)
        if isinstance(prompt, list):
            # Assume format: [{"role": "user", "content": "..."}]
            prompt_str = "\n".join(
                msg.get("content", "") for msg in prompt if msg.get("content")
            )
        else:
            prompt_str = prompt

        try:
            # Step 1: Get raw LLM response via common.llm.ask()
            raw_response = await ask(
                prompt=prompt_str,
                system=system_prompt or "",
                model=self.model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_cache=enable_cache,
                log_level=LogLevel.WARNING,
            )

            # Step 2: Extract structured output if schema provided
            if schema:
                try:
                    structured_output = StructuredOutputExtractor.extract(
                        raw_text=raw_response,
                        model_class=schema,
                        strict=True,
                    )

                    logger.debug(
                        f"Structured extraction successful: model={self.model_name}, "
                        f"schema={schema.__name__}"
                    )

                    return structured_output

                except (ExtractionError, Exception) as e:
                    logger.error(
                        f"Structured extraction failed: model={self.model_name}, "
                        f"schema={schema.__name__}, error={str(e)}, "
                        f"raw_response_preview={_sanitize_for_logging(raw_response, 300)}"
                    )
                    raise LLMError(
                        f"Failed to extract structured output: {str(e)}",
                        provider="openai",
                        model=self.model_name,
                    ) from e

            return raw_response

        except (LLMRateLimitError, LLMTimeoutError, LLMConnectionError) as e:
            # Retryable errors - will be retried by @retry decorator
            logger.warning(
                f"Retryable LLM error: model={self.model_name}, "
                f"error_type={type(e).__name__}, error={str(e)}"
            )
            raise

        except LLMError as e:
            # Non-retryable LLM errors (auth, validation, etc.)
            logger.error(
                f"LLM call failed: model={self.model_name}, "
                f"error_type={type(e).__name__}, error={str(e)}"
            )
            raise

        except Exception as e:
            # Unexpected errors
            logger.error(
                f"Unexpected error in LLM call: model={self.model_name}, "
                f"error_type={type(e).__name__}, error={str(e)}"
            )
            raise LLMError(
                f"Unexpected error during generation: {str(e)}",
                provider="openai",
                model=self.model_name,
            ) from e

    def get_model_name(self) -> str:
        """Get the model identifier.

        Returns:
            Model name string
        """
        return self.model_name


__all__ = ["OpenAIModel", "DEFAULT_OPENAI_MODEL"]
