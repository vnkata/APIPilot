import logging
import random
import re
from api_testing.models.base_model import APITestingBaseLLMModel
from google import genai
from typing import Any, Optional, List, Union
from google.genai import types
from pydantic import BaseModel

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
    wait_fixed,
    RetryCallState,
)

from api_testing.utils.llm_tracker import add_usage

def log_retry_error(retry_state: RetryCallState):
    exception = retry_state.outcome.exception()
    logging.error(
        f"Confident AI Error: {exception}. Retrying: {retry_state.attempt_number} time(s)..."
    )


default_gemini_model = "gemini-2.0-flash"


class GeminiModel(APITestingBaseLLMModel):
    """Class that implements Google Gemini models.

    This class provides integration with Google's Gemini models through the Google GenAI SDK,
    supporting text-only inputs.
    To use Gemini API, set api_key attribute only.
    To use Vertex AI API, set project and location attributes.

    Attributes:
        model_name: Name of the Gemini model to use
        api_key: Google API key for authentication
        project: Google Cloud project ID
        location: Google Cloud location

    Example:
        ```python
        from api_testing.models import GeminiModel

        # Initialize the model
        model = GeminiModel(
            model_name="gemini-1.5-pro-001",
            api_key="your-api-key"
        )

        # Generate text
        response = model.generate("What is the capital of VietNam?")
        ```
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        project: Optional[str] = None,
        location: Optional[str] = None,
        temperature: float = 0.7,
        *args,
        **kwargs,
    ):
        model_name = (
            model_name
            or default_gemini_model
        )

        # Get API key from key handler if not provided
        self.api_key = api_key
        self.project = project
        self.location = location
        self.use_vertexai = False
        if temperature < 0:
            raise ValueError("Temperature must be >= 0.")
        self.temperature = temperature
        super().__init__(model_name, *args, **kwargs)

    def should_use_vertexai(self):
        """Checks if the model should use Vertex AI for generation.

        This is determined first by the value of `GOOGLE_GENAI_USE_VERTEXAI`
        environment variable. If not set, it checks for the presence of the
        project and location.

        Returns:
            True if the model should use Vertex AI, False otherwise
        """
        if self.use_vertexai is not None:
            return self.use_vertexai
        if self.project and self.location:
            return True
        else:
            return False

    def load_model(self, *args, **kwargs):
        """Creates a client.
        With Gen AI SDK, model is set at inference time, so there is no
        model to load and initialize.
        This method name is kept for compatibility with other LLMs.

        Returns:
            A GenerativeModel instance.
        """
        
        if self.should_use_vertexai():
            if not self.project or not self.location:
                raise ValueError(
                    "When using Vertex AI API, both project and location are required."
                    "Either provide them as arguments or set GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION environment variables, "
                    "or set them in your configuration."
                )

            # Create client for Vertex AI
            self.client = genai.Client(
                vertexai=True, project=self.project, location=self.location
            )
        else:
            if not self.api_key:
                raise ValueError(
                    "Google API key is required. Either provide it directly, set GOOGLE_API_KEY environment variable, "
                    "or set it in your configuration."
                )
            # Create client for Gemini API
            # self.client = genai.Client(api_key=self.api_key)
            self.client = genai.Client(api_key=random.choice(self.api_key.split(",")))
        # Configure default model generation settings
        self.model_safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ]
        return self.client.models

    @retry(
        wait=wait_fixed(60),
        stop=stop_after_attempt(3),
        after=log_retry_error,
    )
    def generate(self, prompt: Union[str, List], system_prompt=None, schema: Optional[BaseModel] = None, ) -> str:
        """Generates text from a prompt.

        Args:
            prompt: Text prompt
            schema: Optional Pydantic model for structured output

        Returns:
            Generated text response or structured output as Pydantic model
        """
        self.model = self.load_model()
        configure_params =  {
            # "response_mime_type": "application/json",
            "safety_settings": self.model_safety_settings,
            "temperature": self.temperature,
            "thinking_config": types.ThinkingConfig(
                thinking_budget=0
            )
        }
        if system_prompt:
            configure_params["system_instruction"] = system_prompt
        if schema is not None:
            # configure_params["response_schema"] = schema
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**configure_params),
            )
            cleaned = re.sub(r"^```json\s*|\s*```$", "", response.text.strip(), flags=re.MULTILINE)
            usage = getattr(response, "usage_metadata", None)
            if usage:
                prompt_tokens = getattr(usage, "prompt_token_count", 0)
                completion_tokens = getattr(usage, "candidates_token_count", 0)
                add_usage(prompt_tokens, completion_tokens)
            return schema.model_validate_json(cleaned), 0
        else:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**configure_params),
            )
            usage = getattr(response, "usage_metadata", None)
            if usage:
                prompt_tokens = getattr(usage, "prompt_token_count", 0)
                completion_tokens = getattr(usage, "candidates_token_count", 0)
                add_usage(prompt_tokens, completion_tokens)
            return schema.model_validate_json(cleaned), 0

    async def a_generate(
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> str:
        """Asynchronously generates text from a prompt.

        Args:
            prompt: Text prompt
            schema: Optional Pydantic model for structured output

        Returns:
            Generated text response or structured output as Pydantic model
        """
        if schema is not None:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    safety_settings=self.model_safety_settings,
                    temperature=self.temperature,
                ),
            )
            return response.parsed, 0
        else:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    safety_settings=self.model_safety_settings,
                    temperature=self.temperature,
                ),
            )
            return response.text, 0

    def get_model_name(self) -> str:
        """Returns the name of the Gemini model being used."""
        return self.model_name
