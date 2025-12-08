from api_testing.models.base_model import APITestingBaseEmbeddingModel
from typing import Any, Optional, List
import torch

default_huggingface_embedding_model = 'flax-sentence-embeddings/st-codesearch-distilroberta-base'


class HuggingfaceEmbeddingModel(APITestingBaseEmbeddingModel):
    _model_instance = None  # Singleton model

    def __init__(
        self,
        model: Optional[str] = None,
        use_half=False
    ):
        self.model_name = model if model else default_huggingface_embedding_model
        self.use_half = use_half
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def embed(self, text: str | List[str]) -> List[float] | List[List[float]]:
        if isinstance(text, list):
            return self.embed_texts(text)
        return self.embed_text(text)

    def embed_text(self, text: str) -> List[float]:
        return self.load_model(use_half=self.use_half).encode(
            text, device=self.device, convert_to_tensor=True, batch_size=1)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.load_model(use_half=self.use_half).encode(
            texts, device=self.device, convert_to_tensor=True, batch_size=1)

    async def a_embed_text(self, text: str) -> List[float]:
        return self.embed_text(text)

    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        return self.embed_texts(texts)

    def get_model_name(self) -> str:
        return self.model_name

    def load_model(self, async_mode=False, use_half=False):
        if HuggingfaceEmbeddingModel._model_instance is None:
            print("Loading Huggingface model:", self.model_name,
                  " wtih device: ", self.device)
            from sentence_transformers import SentenceTransformer, util
            HuggingfaceEmbeddingModel._model_instance = SentenceTransformer(
                self.model_name,
                device=self.device,
                model_kwargs={'torch_dtype': torch.float16} if use_half else {}
            )
        return HuggingfaceEmbeddingModel._model_instance
