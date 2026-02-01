"""
Model Factory for API Testing LLM Models.

Provides centralized model instantiation with environment-based configuration.
"""

import os
from typing import Optional

from api_testing.models.base_model import APITestingBaseLLMModel
from common.logger import LogLevel, get_logger

logger = get_logger("model_factory", level=LogLevel.INFO)


class ModelFactory:
    """Factory for creating LLM model instances based on configuration.

    Supports environment variable configuration:
        LLM_PROVIDER: Model provider (openai, gemini, ollama, azure, litellm, local)
        LLM_MODEL: Specific model name (e.g., gpt-4, gemini-2.0-flash)
        LLM_TEMPERATURE: Default temperature (0.0-2.0)
        LLM_BASE_URL: Base URL for custom endpoints (optional)

    Example:
        >>> # Use default (OpenAI)
        >>> model = ModelFactory.get_default()
        >>>
        >>> # Override via env vars
        >>> os.environ["LLM_PROVIDER"] = "gemini"
        >>> os.environ["LLM_MODEL"] = "gemini-2.0-flash"
        >>> model = ModelFactory.get_default()  # Returns GeminiModel
    """

    _default_model: Optional["APITestingBaseLLMModel"] = None

    @classmethod
    def get_default(cls) -> "APITestingBaseLLMModel":
        """Get or create the default LLM model instance.

        Reads configuration from environment variables:
        - LLM_PROVIDER: Provider name (default: openai)
        - LLM_MODEL: Model name (provider-specific default if not set)
        - LLM_TEMPERATURE: Temperature (default: 0.7)

        Returns:
            Configured LLM model instance

        Raises:
            ValueError: If LLM_PROVIDER is unsupported
        """
        if cls._default_model is not None:
            return cls._default_model

        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        model_name = os.getenv("LLM_MODEL", "")
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        base_url = os.getenv("LLM_BASE_URL", "")

        logger.info(
            f"Creating default LLM model: provider={provider}, "
            f"model={model_name or 'default'}, temperature={temperature}"
        )

        if provider == "openai":
            from api_testing.models.llms.openai_model import OpenAIModel

            cls._default_model = OpenAIModel(
                model=model_name or None,
                temperature=temperature,
            )
        elif provider == "gemini":
            from api_testing.models.llms.gemini_model import GeminiModel

            cls._default_model = GeminiModel(
                model=model_name or None,
                temperature=temperature,
            )
        elif provider == "ollama":
            from api_testing.models.llms.ollama_model import OllamaModel

            cls._default_model = OllamaModel(
                model=model_name or None,
                temperature=temperature,
                base_url=base_url or None,
            )
        elif provider == "azure":
            from api_testing.models.llms.AzureOpenAIModel import AzureOpenAIModel

            cls._default_model = AzureOpenAIModel(
                model=model_name or None,
                temperature=temperature,
            )
        elif provider == "litellm":
            from api_testing.models.llms.litellm_model import LiteLLMModel

            cls._default_model = LiteLLMModel(
                model=model_name or None,
                temperature=temperature,
            )
        elif provider == "local":
            from api_testing.models.llms.local_model import LocalModel

            cls._default_model = LocalModel(
                model=model_name or None,
                temperature=temperature,
            )
        else:
            raise ValueError(
                f"Unsupported LLM_PROVIDER: {provider}. "
                f"Supported: openai, gemini, ollama, azure, litellm, local"
            )

        logger.info(f"Default model created: {cls._default_model.get_model_name()}")
        return cls._default_model

    @classmethod
    def reset_default(cls) -> None:
        """Reset the cached default model instance.

        Useful for testing or when environment variables change.
        """
        cls._default_model = None
        logger.debug("Default model cache reset")


__all__ = ["ModelFactory"]
