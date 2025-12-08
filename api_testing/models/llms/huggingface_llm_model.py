import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Any, Optional, List

from api_testing.models.base_model import APITestingBaseLLMModel


class HuggingfaceLLMModel(APITestingBaseLLMModel):
    # Singleton model
    _model_instance: Optional[AutoModelForCausalLM] = None
    _tokenizer_instance: Optional[AutoTokenizer] = None

    def __init__(
        self,
        model,
        # tokenizer,
    ):
        self.model = model,
        self.device = 'cuda'

    def get_model_name(self):
        return self.model

    def load_model(self):
        if HuggingfaceLLMModel._model_instance is None:
            HuggingfaceLLMModel._model_instance = AutoModelForCausalLM.from_pretrained(
                self.model, device_map='auto')
            HuggingfaceLLMModel._tokenizer_instance = AutoTokenizer.from_pretrained(
                self.model)
        return HuggingfaceLLMModel._model_instance, HuggingfaceLLMModel._tokenizer_instance

    def generate(self, prompt: str) -> str:

        model, tokenizer = self.load_model()  # assume already use device_map='auto'

        model_inputs = tokenizer(
            [prompt], return_tensors="pt").to(self.device)

        generated_ids = model.generate(
            **model_inputs, max_new_tokens=-1, do_sample=True)
        return self.tokenizer.batch_decode(generated_ids)[0]

    async def a_generate(self, prompt: str) -> str:
        '''
        5. implement the a_generate() method, with the same function signature as generate(). Note that this is an async method.
        '''
        return self.generate(prompt)
