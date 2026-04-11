import logging
import os
import json
from openai import AzureOpenAI, AsyncAzureOpenAI
from typing import List, Optional, Tuple, Union, Dict

from pydantic import BaseModel

from api_testing.models.base_model import APITestingBaseLLMModel


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
                parsed = schema.model_validate_json(text)
                return parsed, 0
            except Exception:
                try:
                    cleaned = text.strip("```json").strip("```").strip()
                    parsed = schema.model_validate_json(cleaned)
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
                parsed = schema.model_validate_json(text)
                return parsed, 0
            except Exception:
                logging.error("Async JSON parse failed")
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