from openai import OpenAI
from typing import List, Optional, Tuple, Union, Dict

from pydantic import BaseModel

from api_testing.models.base_model import APITestingBaseLLMModel
from api_testing.utils import remove_think_tags


class LocalModel(APITestingBaseLLMModel):
    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs,
    ):
        self.model_name = model
        self.base_url = (
            base_url
            or "https://integrate.api.nvidia.com/v1"
        )
        self.api_key = api_key
        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature
        super().__init__(model)

    ###############################################
    # Other generate functions
    ###############################################

    def generate(
        self, prompt:  Union[str, List], schema: Optional[BaseModel] = None
    ) -> Tuple[Union[str, Dict], float]:
        chat_model = self.load_model()

        response = chat_model.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        return (
            (
                schema.model_validate_json(response.choices[0].message)
                if schema
                else remove_think_tags(response.choices[0].message)
            ),
            0
        )

    async def a_generate(
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> Tuple[str, float]:
        chat_model = self.load_model()

        response = chat_model.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature
        )
        return (
            (
                schema.model_validate_json(response.choices[0].message)
                if schema
                else remove_think_tags(response.choices[0].message)
            ),
            0
        )

    ###############################################
    # Model
    ###############################################

    def load_model(self, async_mode: bool = False):
        return OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def get_model_name(self):
        return f"{self.model_name} (Local)"
