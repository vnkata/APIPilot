
from ollama import Client, AsyncClient
from typing import Any, Optional, List
from api_testing.models.base_model import APITestingBaseEmbeddingModel


class OllamaEmbeddingModel(APITestingBaseEmbeddingModel):
    def __init__(self, base_url, model_name, api_key=None):
        self.base_url = base_url
        self.model_name = model_name
        self.api_key = api_key
        super().__init__(model_name)

    def load_model(self, async_mode: bool = False):
        if not async_mode:
            return Client(host=self.base_url)
        else:
            return AsyncClient(host=self.base_url)

    def embed(self, text: str | List[str]) -> List[float] | List[List[float]]:
        if isinstance(text, list):
            return self.embed_texts(text)
        return self.embed_text(text)

    def embed_text(self, text: str) -> List[float]:
        embedding_model = self.load_model()
        response = embedding_model.embed(
            model=self.model_name,
            input=text,
        )
        return response["embeddings"][0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embedding_model = self.load_model()
        response = embedding_model.embed(
            model=self.model_name,
            input=texts,
        )
        return response["embeddings"]

    async def a_embed_text(self, text: str) -> List[float]:
        embedding_model = self.load_model(async_mode=True)
        response = await embedding_model.embed(
            model=self.model_name,
            input=text,
        )
        return response["embeddings"][0]

    async def a_embed_texts(self, texts: List[str]) -> List[List[float]]:
        embedding_model = self.load_model(async_mode=True)
        response = await embedding_model.embed(
            model=self.model_name,
            input=texts,
        )
        return response["embeddings"]

    def get_model_name(self):
        return self.model_name
