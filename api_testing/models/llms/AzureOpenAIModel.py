import os
import json
from openai import AzureOpenAI, AsyncAzureOpenAI
from typing import List, Optional, Tuple, Union, Dict

from pydantic import BaseModel

from api_testing.models.base_model import APITestingBaseLLMModel
from api_testing.utils import remove_think_tags


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
        prompt: Union[str, List], 
        schema: Optional[BaseModel] = None,
        system_prompt: Optional[str] = None,
    ) -> Tuple[Union[str, Dict], float]:
        client = self.load_model()

        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # If schema is provided, add instructions to ensure proper JSON format
        if schema:
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            schema_instruction = (
                f"\n\nYou must respond with valid JSON that matches this exact schema. "
                f"IMPORTANT: All fields defined as 'array' type must be arrays (lists), even if there's only one value. "
                f"Never use a single string where an array is expected.\n\nSchema:\n{schema_json}"
            )
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += schema_instruction
            else:
                messages.insert(0, {"role": "system", "content": schema_instruction})
        
        messages.append({"role": "user", "content": prompt})
        
        if schema:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
        else:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
            )
        
        content = response.choices[0].message.content
        
        if schema:
            # Try to fix common issues before validation
            try:
                return schema.model_validate_json(content), 0
            except Exception as e:
                # Try to fix the JSON by converting single values to arrays
                fixed_content = self._fix_json_arrays(content, schema)
                return schema.model_validate_json(fixed_content), 0
        else:
            return remove_think_tags(content), 0

    async def a_generate(
        self, 
        prompt: str, 
        schema: Optional[BaseModel] = None,
        system_prompt: Optional[str] = None,
    ) -> Tuple[str, float]:
        client = self.load_model(async_mode=True)

        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if schema:
            schema_json = json.dumps(schema.model_json_schema(), indent=2)
            schema_instruction = (
                f"\n\nYou must respond with valid JSON that matches this exact schema. "
                f"IMPORTANT: All fields defined as 'array' type must be arrays (lists), even if there's only one value. "
                f"Never use a single string where an array is expected.\n\nSchema:\n{schema_json}"
            )
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += schema_instruction
            else:
                messages.insert(0, {"role": "system", "content": schema_instruction})
        
        messages.append({"role": "user", "content": prompt})
        
        if schema:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )
        else:
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
            )
        
        content = response.choices[0].message.content
        
        if schema:
            try:
                return schema.model_validate_json(content), 0
            except Exception:
                fixed_content = self._fix_json_arrays(content, schema)
                return schema.model_validate_json(fixed_content), 0
        else:
            return remove_think_tags(content), 0

    def _fix_json_arrays(self, content: str, schema: BaseModel) -> str:
        """Fix JSON where single strings should be arrays."""
        try:
            data = json.loads(content)
            schema_dict = schema.model_json_schema()
            
            def fix_arrays(obj, schema_props):
                if not isinstance(obj, dict) or not schema_props:
                    return obj
                
                for key, value in obj.items():
                    if key in schema_props:
                        prop_schema = schema_props[key]
                        # Check if this should be an array
                        if prop_schema.get("type") == "array" and isinstance(value, str):
                            obj[key] = [value]
                        elif isinstance(value, dict):
                            # Handle nested objects
                            nested_props = prop_schema.get("properties", {})
                            if not nested_props and "$ref" in prop_schema:
                                # Handle $ref - simplified
                                pass
                            fix_arrays(value, nested_props)
                        elif isinstance(value, dict):
                            # Handle additionalProperties (like Dict[str, SchemaParam])
                            additional = prop_schema.get("additionalProperties", {})
                            if additional:
                                nested_props = additional.get("properties", {})
                                for nested_key, nested_val in value.items():
                                    if isinstance(nested_val, dict):
                                        fix_arrays(nested_val, nested_props)
                return obj
            
            # Get the properties from schema
            props = schema_dict.get("properties", {})
            fixed_data = fix_arrays(data, props)
            
            # Special handling for the Verdict schema structure
            if "schemas" in fixed_data and isinstance(fixed_data["schemas"], dict):
                for schema_name, schema_params in fixed_data["schemas"].items():
                    if isinstance(schema_params, dict):
                        for param_key, param_value in schema_params.items():
                            if isinstance(param_value, str):
                                fixed_data["schemas"][schema_name][param_key] = [param_value]
            
            return json.dumps(fixed_data)
        except Exception:
            return content

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