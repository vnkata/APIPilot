import logging
import json
from typing import Optional, List, Union
from dotenv.main import os
from pydantic import BaseModel
from openai import OpenAI, AsyncOpenAI

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    RetryCallState,
    wait_fixed,
)

from api_testing.models.base_model import APITestingBaseLLMModel
from api_testing.utils.llm_tracker import add_usage
from dotenv import load_dotenv

load_dotenv()


def log_retry_error(retry_state: RetryCallState):
    exception = retry_state.outcome.exception()
    logging.error(
        f"OpenAI Error: {exception}. Retrying: {retry_state.attempt_number} time(s)..."
    )


default_model = "gpt-4.1-mini"

NO_TEMPERATURE_MODELS = (
    "gpt-5",
    "o3",
    "o4",
)

def supports_temperature(model: str) -> bool:
    return not model.startswith(NO_TEMPERATURE_MODELS)

class OpenAIModel(APITestingBaseLLMModel):
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.0,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        self.model_name = model or default_model

        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature

        self.api_key = api_key
        self.base_url = base_url

        super().__init__(self.model_name, **kwargs)

    # ========================
    # Load model / client
    # ========================
    def load_model(self, *args, **kwargs):
        self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY or pass api_key."
            )

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        self.async_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        return self.client

    # ========================
    # Sync generate
    # ========================
    @retry(
        wait=wait_fixed(60),
        stop=stop_after_attempt(3),
        after=log_retry_error,
    )
    def generate(
        self,
        prompt: Union[str, List[dict]],
        system_prompt: Optional[str] = None,
        schema: Optional[BaseModel] = None,
        caller=None,
    ):
        messages = []

        if system_prompt:
            schema_instruction = """Think step by step and strictly follow all requirements in the user prompt. Return only valid JSON that exactly matches the specified structure, without any extra text or fields, and ensure it is fully syntactically correct. """
            messages.append({"role": "system", "content": schema_instruction})

        if isinstance(prompt, str):
            messages.append({"role": "user", "content": system_prompt + "\n" + prompt})
        else:
            messages.extend(prompt)
        kwargs = {
            "model": self.model_name,
            "messages": messages,
        }
        if supports_temperature(self.model_name):
            kwargs["temperature"] = self.temperature
        else:
            kwargs["reasoning_effort"] = "minimal"
        response = self.client.chat.completions.create(**kwargs)

        # ===== usage tracking =====
        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        cached_tokens=getattr(
        usage.prompt_tokens_details,
            "cached_tokens",
            0
        ) if getattr(usage, "prompt_tokens_details", None) else 0
        reasoning_tokens=getattr(
            usage.completion_tokens_details,
            "reasoning_tokens",
            0
        ) if getattr(usage, "completion_tokens_details", None) else 0
        text = response.choices[0].message.content.strip()

        # ===== structured output =====
        if schema:
            try:
                # print(text)
                parsed = schema.model_validate_json(text)
                add_usage(caller, prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens)

                return parsed, 0
            except Exception:
                try:
                    cleaned = text.strip("```json").strip("```").strip()
                    parsed = schema.model_validate_json(cleaned)
                    add_usage(prompt_tokens, completion_tokens)
                    return parsed, 0
                except Exception as e:
                    raise Exception(f"JSON parse failed: {e}")

        return text, 0

    # ========================
    # Async generate
    # ========================
    @retry(
        wait=wait_exponential_jitter(initial=1, max=20),
        stop=stop_after_attempt(3),
        after=log_retry_error,
    )
    async def a_generate(
        self,
        prompt: Union[str, List[dict]],
        system_prompt: Optional[str] = None,
        schema: Optional[BaseModel] = None,
    ):
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if isinstance(prompt, str):
            messages.append({"role": "user", "content": prompt})
        else:
            messages.extend(prompt)
        kwargs = {
            "model": self.model_name,
            "messages": messages,
        }
        if supports_temperature(self.model_name):
            kwargs["temperature"] = self.temperature
        else:
            kwargs["reasoning"] = {"effort": "minimal"}

        response = await self.async_client.chat.completions.create(**kwargs)

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        add_usage(prompt_tokens, completion_tokens)

        text = response.choices[0].message.content.strip()

        if schema:
            try:
                parsed = schema.model_validate_json(text)
                return parsed, 0
            except Exception:
                logging.error("Async JSON parse failed")
                return text, 0

        return text, 0

    # ========================
    # Batch (simple version)
    # ========================
    def batch_generate(self, prompts: List[str]):
        return [self.generate(p) for p in prompts]

    # ========================
    # Model name
    # ========================
    def get_model_name(self) -> str:
        return self.model_name
