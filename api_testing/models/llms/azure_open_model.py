import logging
import os
import json
from openai import AzureOpenAI, AsyncAzureOpenAI
from typing import Iterable, List, Optional, Tuple, Union, Dict

from pydantic import BaseModel

from api_testing.models.base_model import APITestingBaseLLMModel


def _strip_json_fence(text: str) -> str:
    """Remove a full-response markdown JSON code fence when present."""
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
    """Yield possible JSON documents from an LLM response."""
    seen: set[str] = set()
    direct_candidates = [text.strip(), _strip_json_fence(text)]

    for candidate in direct_candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate

    source = _strip_json_fence(text)
    decoder = json.JSONDecoder()
    for index, char in enumerate(source):
        if char not in "{[":
            continue
        try:
            _, end_index = decoder.raw_decode(source[index:])
        except json.JSONDecodeError:
            continue

        candidate = source[index:index + end_index].strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            yield candidate


def _validate_schema_json(text: str, schema: BaseModel):
    """Validate structured output, tolerating prose around the JSON block."""
    last_error: Exception | None = None
    for candidate in _json_candidates(text):
        try:
            return schema.model_validate_json(candidate)
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise ValueError("No JSON object or array found in model response")


class AzureOpenAIModel(APITestingBaseLLMModel):
    """Class that implements Azure OpenAI models."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_version: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ):
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
        
        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key is required. Either provide it directly or set AZURE_OPENAI_KEY environment variable."
            )
        if not self.endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. Either provide it directly or set AZURE_OPENAI_ENDPOINT environment variable."
            )
        
        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature
        
        super().__init__(model)

    ###############################################
    # Generate functions
    ###############################################

    def generate(
        self, 
        prompt: Union[str, List[dict]], 
        schema: Optional[BaseModel] = None,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Union[str, Dict], float]:
        client = self.load_model()

        messages = []
        
        if system_prompt:
            schema_instruction = (
                "Think step by step and strictly follow all requirements in the user prompt. "
                "Return only valid JSON that exactly matches the specified structure, "
                "without any extra text or fields, and ensure it is fully syntactically correct. "
            )
            messages.append({"role": "system", "content": schema_instruction})
        
        if isinstance(prompt, str):
            messages.append({"role": "user", "content": system_prompt + "\n" + prompt})
        else:
            messages.extend(prompt)
        
        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
        )

        text = response.choices[0].message.content.strip()
        
        if schema:
            try:
                parsed = _validate_schema_json(text, schema)
                return parsed, 0
            except Exception as e:
                raise Exception(f"JSON parse failed: {e}")

        return text, 0

    async def a_generate(
        self, 
        prompt: Union[str, List[dict]],
        schema: Optional[BaseModel] = None,
        system_prompt: Optional[str] = None,
    ) -> Tuple[str, float]:
        client = self.load_model(async_mode=True)

        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if isinstance(prompt, str):
            messages.append({"role": "user", "content": prompt})
        else:
            messages.extend(prompt)
        
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
        )

        text = response.choices[0].message.content.strip()

        if schema:
            try:
                parsed = _validate_schema_json(text, schema)
                return parsed, 0
            except Exception as e:
                logging.error(f"Async JSON parse failed: {e}\nResponse: {text[:500]}")
                return text, 0

        return text, 0

    ###############################################
    # Model
    ###############################################

    def load_model(self, async_mode: bool = False):
        if async_mode:
            return AsyncAzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.endpoint,
            )
        return AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint,
        )

    def get_model_name(self):
        return f"{self.model_name} (Azure OpenAI)"
