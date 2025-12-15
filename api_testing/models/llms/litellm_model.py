from api_testing.models.base_model import APITestingBaseLLMModel
from ollama import Client, AsyncClient, ChatResponse
from typing import List, Optional, Tuple, Union, Dict
from google.genai import types
from pydantic import BaseModel

from api_testing.utils import remove_think_tags

default_gemini_model = "gemini-2.0-flash"


class LiteLLMModel(APITestingBaseLLMModel):
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ):
        model_name = model
        self.base_url = (
            base_url
            or "http://localhost:11434"
        )
        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature
        super().__init__(model_name)

    ###############################################
    # Other generate functions
    ###############################################

    def generate(
        self, prompt:  Union[str, List], schema: Optional[BaseModel] = None
    ) -> Tuple[Union[str, Dict], float]:
        chat_model = self.load_model()

        response: ChatResponse = chat_model.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            format=schema.model_json_schema() if schema else None,
            options={"temperature": self.temperature},
        )
        return (
            (
                schema.model_validate_json(response.message.content)
                if schema
                else remove_think_tags(response.message.content)
            ),
            0,
        )

    async def a_generate(
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> Tuple[str, float]:
        chat_model = self.load_model(async_mode=True)
        response: ChatResponse = await chat_model.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            format=schema.model_json_schema() if schema else None,
            options={"temperature": self.temperature},
        )
        return (
            (
                schema.model_validate_json(response.message.content)
                if schema
                else remove_think_tags(response.message.content)
            ),
            0,
        )

    ###############################################
    # Model
    ###############################################

    def load_model(self, async_mode: bool = False):
        if not async_mode:
            return Client(host=self.base_url)
        else:
            return AsyncClient(host=self.base_url)

    def get_model_name(self):
        return f"{self.model_name} (Ollama)"
