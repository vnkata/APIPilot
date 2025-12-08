from api_testing.models.base_model import APITestingBaseEmbeddingModel
from typing import Any, Optional, List
import torch

default_huggingface_embedding_model = 'flax-sentence-embeddings/st-codesearch-distilroberta-base'


class VLLMEmbeddingModel(APITestingBaseEmbeddingModel):
    _model_instance = None  # Singleton model

    def __init__(
        self,
        model: Optional[str] = None,
        use_half=False
    ):
        self.model_name = model if model else default_huggingface_embedding_model
        self._initialized = True  # Mark as initialized
        self.use_half = use_half
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def embed(self, text: str | List[str]) -> List[float] | List[List[float]]:
        if isinstance(text, list):
            return self.embed_texts(text)
        return self.embed_text(text)

    def embed_text(self, text: str) -> List[float]:
        client = self.load_model(async_mode=False)
        response = client.embed(text)
        return response

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        client = self.load_model(async_mode=False)
        response = client.embed(texts)
        return response

    async def a_embed_text(self, text: str) -> List[float]:
        return self.embed_text(text)

    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.embed_texts(texts)

    def get_model_name(self) -> str:
        return self.model_name

    def load_model(self, async_mode: bool, use_half=False):
        if VLLMEmbeddingModel._model_instance is None:
            try:
                from vllm import LLM
            except ImportError:
                error_message = "Failed to import module 'vllm'"
                installation_guide = [
                    "Please make sure 'vllm' is installed. ",
                    "You can install it by `pip install vllm`\n",
                ]

                raise ImportError(
                    f"{error_message}\n\n{''.join(installation_guide)}")

            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            VLLMEmbeddingModel._model_instance = LLM(
                model=self.model_name, task="embed")

        return VLLMEmbeddingModel._model_instance
