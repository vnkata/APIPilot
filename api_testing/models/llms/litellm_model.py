"""
LiteLLM Model Implementation

This module provides a unified interface for various LLM providers using the litellm library.
"""

import logging
import json
from typing import Optional, List, Union, Tuple, Dict, Any
from pydantic import BaseModel
import litellm

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    RetryCallState,
    wait_fixed,
)

from api_testing.models.base_model import APITestingBaseLLMModel
from api_testing.utils.llm_tracker import add_usage
from api_testing.utils import remove_think_tags


def log_retry_error(retry_state: RetryCallState):
    """Log retry errors for debugging."""
    exception = retry_state.outcome.exception()
    logging.error(
        f"LiteLLM Error: {exception}. Retrying: {retry_state.attempt_number} time(s)..."
    )


class LiteLLMModel(APITestingBaseLLMModel):
    """
    LiteLLM model implementation supporting multiple LLM providers.

    This class provides a unified interface to various LLM providers through litellm,
    including OpenAI, Anthropic, Google, and many others.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        """
        Initialize the LiteLLM model.

        Args:
            model: Model name (e.g., 'gpt-4', 'claude-3', 'gemini-pro')
            temperature: Sampling temperature (0.0 to 1.0)
            api_key: API key for the provider
            base_url: Custom base URL for API calls
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments passed to litellm
        """
        self.model_name = model or "gpt-4o-mini"

        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature
        self.api_key = api_key
        self.base_url = base_url
        self.max_tokens = max_tokens
        self.extra_kwargs = kwargs

        # Set API key if provided
        if self.api_key:
            # Extract provider from model name for API key setting
            provider = self._get_provider_from_model(self.model_name)
            if provider:
                litellm.api_key = self.api_key

        super().__init__(self.model_name, **kwargs)

    def _get_provider_from_model(self, model_name: str) -> Optional[str]:
        """Extract provider name from model string."""
        # Common provider prefixes
        providers = {
            'gpt-': 'openai',
            'claude-': 'anthropic',
            'gemini-': 'google',
            'llama': 'ollama',
            'mistral': 'mistral',
            'command': 'cohere',
        }

        for prefix, provider in providers.items():
            if model_name.startswith(prefix):
                return provider
        return None

    def load_model(self, *args, **kwargs):
        """
        Load the model. For LiteLLM, this is a no-op since litellm handles model loading internally.

        Returns:
            None (litellm handles model management)
        """
        return None

    @retry(
        wait=wait_fixed(60),
        stop=stop_after_attempt(3),
        after=log_retry_error,
    )
    def generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        schema: Optional[BaseModel] = None,
    ) -> Tuple[Union[str, BaseModel], float]:
        """
        Generate text using the LLM.

        Args:
            prompt: Input prompt (string or list of messages)
            system_prompt: System prompt to prepend
            schema: Pydantic schema for structured output

        Returns:
            Tuple of (response, cost_estimate)
        """
        messages = self._prepare_messages(prompt, system_prompt)

        # Prepare call arguments
        call_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            **self.extra_kwargs
        }

        if self.max_tokens:
            call_kwargs["max_tokens"] = self.max_tokens

        if schema:
            call_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = litellm.completion(**call_kwargs)

            # Extract usage information
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

            # Track usage
            add_usage(prompt_tokens, completion_tokens)

            # Extract response text
            text = response.choices[0].message.content.strip()

            # Handle structured output
            if schema:
                try:
                    parsed = schema.model_validate_json(text)
                    return parsed, self._estimate_cost(prompt_tokens, completion_tokens)
                except Exception:
                    # Try cleaning the response
                    try:
                        cleaned = text.strip("```json").strip("```").strip()
                        parsed = schema.model_validate_json(cleaned)
                        return parsed, self._estimate_cost(prompt_tokens, completion_tokens)
                    except Exception as e:
                        raise Exception(f"JSON parse failed: {e}")

            # Return cleaned text for regular generation
            return remove_think_tags(text), self._estimate_cost(prompt_tokens, completion_tokens)

        except Exception as e:
            logging.error(f"LiteLLM generation failed: {e}")
            raise

    @retry(
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(3),
        after=log_retry_error,
    )
    async def a_generate(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None,
        schema: Optional[BaseModel] = None,
    ) -> Tuple[Union[str, BaseModel], float]:
        """
        Async generate text using the LLM.

        Args:
            prompt: Input prompt (string or list of messages)
            system_prompt: System prompt to prepend
            schema: Pydantic schema for structured output

        Returns:
            Tuple of (response, cost_estimate)
        """
        messages = self._prepare_messages(prompt, system_prompt)

        # Prepare call arguments
        call_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            **self.extra_kwargs
        }

        if self.max_tokens:
            call_kwargs["max_tokens"] = self.max_tokens

        if schema:
            call_kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await litellm.acompletion(**call_kwargs)

            # Extract usage information
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

            # Track usage
            add_usage(prompt_tokens, completion_tokens)

            # Extract response text
            text = response.choices[0].message.content.strip()

            # Handle structured output
            if schema:
                try:
                    parsed = schema.model_validate_json(text)
                    return parsed, self._estimate_cost(prompt_tokens, completion_tokens)
                except Exception:
                    # Try cleaning the response
                    try:
                        cleaned = text.strip("```json").strip("```").strip()
                        parsed = schema.model_validate_json(cleaned)
                        return parsed, self._estimate_cost(prompt_tokens, completion_tokens)
                    except Exception as e:
                        raise Exception(f"JSON parse failed: {e}")

            # Return cleaned text for regular generation
            return remove_think_tags(text), self._estimate_cost(prompt_tokens, completion_tokens)

        except Exception as e:
            logging.error(f"Async LiteLLM generation failed: {e}")
            raise

    def _prepare_messages(
        self,
        prompt: Union[str, List[Dict[str, str]]],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Prepare messages for LLM call."""
        messages = []

        if system_prompt:
            schema_instruction = (
                "Think step by step and strictly follow all requirements in the user prompt. "
                "Return only valid JSON that exactly matches the specified structure, "
                "without any extra text or fields, and ensure it is fully syntactically correct."
            )
            messages.append({"role": "system", "content": system_prompt + "\n" + schema_instruction})

        if isinstance(prompt, str):
            messages.append({"role": "user", "content": prompt})
        else:
            messages.extend(prompt)

        return messages

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate cost based on token usage.

        This is a simple estimation. For accurate costs, use the actual pricing
        from the provider or implement more sophisticated cost calculation.
        """
        # Simple cost estimation (can be enhanced with actual pricing)
        # This returns 0 for now as cost tracking is handled elsewhere
        return 0.0

    def get_model_name(self) -> str:
        """Get the full model name with provider info."""
        provider = self._get_provider_from_model(self.model_name)
        provider_name = provider.title() if provider else "Unknown"
        return f"{self.model_name} ({provider_name})"

    def batch_generate(
        self,
        prompts: List[Union[str, List[Dict[str, str]]]],
        system_prompt: Optional[str] = None,
        schema: Optional[BaseModel] = None,
    ) -> List[Tuple[Union[str, BaseModel], float]]:
        """
        Generate responses for multiple prompts.

        Args:
            prompts: List of input prompts
            system_prompt: System prompt to use for all prompts
            schema: Schema for structured output

        Returns:
            List of (response, cost) tuples
        """
        results = []
        for prompt in prompts:
            try:
                result = self.generate(prompt, system_prompt, schema)
                results.append(result)
            except Exception as e:
                logging.error(f"Batch generation failed for prompt: {e}")
                results.append(("", 0.0))  # Return empty result on failure

        return results
