import logging
import json
from typing import Iterable, Optional, List, Union
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


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _json_candidates(text: str) -> Iterable[str]:
    seen: set[str] = set()
    for candidate in (text.strip(), _strip_json_fence(text)):
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate

    source = _strip_json_fence(text)
    decoder = json.JSONDecoder()
    start_index = source.find("{")
    if start_index >= 0:
        try:
            _, end_index = decoder.raw_decode(source[start_index:])
        except json.JSONDecodeError:
            return
        candidate = source[start_index:start_index + end_index].strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def _validate_schema_json(text: str, schema: BaseModel):
    last_error: Exception | None = None
    for candidate in _json_candidates(text):
        try:
            return schema.model_validate_json(candidate)
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise ValueError("No JSON object or array found in model response")


def _build_system_message(
    system_prompt: Optional[str],
    schema: Optional[type[BaseModel]],
) -> Optional[str]:
    system_parts = [system_prompt] if system_prompt else []
    if schema:
        schema_definition = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        system_parts.append(
            "Return only one valid JSON object matching this JSON Schema exactly. "
            f"JSON Schema: {schema_definition}"
        )
    if not system_parts:
        return None
    return "\n\n".join(system_parts)


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
    ):
        messages = []

        system_message = _build_system_message(system_prompt, schema)
        if system_message:
            messages.append({"role": "system", "content": system_message})

        if isinstance(prompt, str):
            messages.append({"role": "user", "content": prompt})
        else:
            messages.extend(prompt)

        request_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
        }
        if schema:
            request_kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**request_kwargs)

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
                parsed = _validate_schema_json(text, schema)
                add_usage(prompt_tokens, completion_tokens, cached_tokens, reasoning_tokens)
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

        system_message = _build_system_message(system_prompt, schema)
        if system_message:
            messages.append({"role": "system", "content": system_message})

        if isinstance(prompt, str):
            messages.append({"role": "user", "content": prompt})
        else:
            messages.extend(prompt)

        request_kwargs = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
        }
        if schema:
            request_kwargs["response_format"] = {"type": "json_object"}

        response = await self.async_client.chat.completions.create(**request_kwargs)

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        add_usage(prompt_tokens, completion_tokens)

        text = response.choices[0].message.content.strip()

        if schema:
            try:
                parsed = _validate_schema_json(text, schema)
                return parsed, 0
            except Exception as e:
                logging.error(f"Async JSON parse failed: {e}\nResponse: {text[:500]}")
                raise

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
