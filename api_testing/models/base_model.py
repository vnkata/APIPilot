from abc import ABC, abstractmethod
from typing import Any, Optional, List


class APITestingBaseLLMModel(ABC):
    def __init__(self, model_name: Optional[str] = None, *args, **kwargs):
        self.model_name = model_name
        self.model = self.load_model(*args, **kwargs)

    @abstractmethod
    def load_model(self, *args, **kwargs):
        """Loads a model, that will be responsible for scoring.

        Returns:
            A model object
        """
        raise NotImplementedError

    @abstractmethod
    def generate(self, *args, **kwargs) -> str:
        """Runs the model to output LLM response.

        Returns:
            A string.
        """
        raise NotImplementedError

    @abstractmethod
    async def a_generate(self, *args, **kwargs) -> str:
        """Runs the model to output LLM response.

        Returns:
            A string.
        """
        raise NotImplementedError

    def batch_generate(self, *args, **kwargs) -> List[str]:
        """Runs the model to output LLM responses.

        Returns:
            A list of strings.
        """
        raise AttributeError

    @abstractmethod
    def get_model_name(self, *args, **kwargs) -> str:
        raise NotImplementedError


class APITestingBaseEmbeddingModel(ABC):
    def __init__(self, model_name: Optional[str] = None, *args, **kwargs):
        self.model_name = model_name
        self.model = self.load_model(*args, **kwargs)

    @abstractmethod
    def load_model(self, *args, **kwargs):
        """Loads a model, that will be responsible for generating text embeddings.

        Returns:
            A model object
        """
        raise NotImplementedError

    @abstractmethod
    def embed(self, *args, **kwargs) -> List[float] | List[List[float]]:

        raise NotImplementedError

    @abstractmethod
    def embed_text(self, *args, **kwargs) -> List[float]:
        """Runs the model to generate text embeddings.

        Returns:
            A list of float.
        """
        raise NotImplementedError

    @abstractmethod
    async def a_embed_text(self, *args, **kwargs) -> List[float]:
        """Runs the model to generate text embeddings.

        Returns:
            A list of list of float.
        """
        raise NotImplementedError

    @abstractmethod
    def embed_texts(self, *args, **kwargs) -> List[List[float]]:
        """Runs the model to generate list of text embeddings.

        Returns:
            A list of float.
        """
        raise NotImplementedError

    @abstractmethod
    async def a_embed_texts(self, *args, **kwargs) -> List[List[float]]:
        """Runs the model to generate list of text embeddings.

        Returns:
            A list of list of float.
        """
        raise NotImplementedError

    @abstractmethod
    def get_model_name(self, *args, **kwargs) -> str:
        raise NotImplementedError
