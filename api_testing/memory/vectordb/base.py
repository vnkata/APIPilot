
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict


class Distance(str, Enum):
    cosine = "cosine"
    l2 = "l2"
    max_inner_product = "max_inner_product"


@dataclass
class Emb:
    """Base class for managing embedders"""

    dimensions: Optional[int] = 1536

    def get_embedding(self, text: str) -> List[float]:
        raise NotImplementedError

    def get_embedding_and_usage(self, text: str) -> Tuple[List[float], Optional[Dict]]:
        embedding = self.get_embedding(text)
        return embedding, None
# {
#                   id: "5a6bee0a-306c-47fc-942b-8ab9bf3899c4",
#                   text: "Document chunk content...",
#                   metadata: {
#                     url: "file://document.txt",
#                     title: "document.txt",
#                     author: "no author specified",
#                     description: "no description found",
#                     docSource: "post:123456",
#                     chunkSource: "document.txt",
#                     published: "12/1/2024, 11:39:39 AM",
#                     wordCount: 8,
#                     tokenCount: 9
#                   },
#                   distance: 0.541887640953064,
#                   score: 0.45811235904693604
#                 }


class Document(BaseModel):
    """Model for managing a document"""
    id: Optional[str] = None
    content: str
    name: Optional[str] = None
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    # usage: Optional[Dict[str, Any]] = None
    # reranking_score: Optional[float] = None
    score: Optional[float] = 0.0
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the document"""

        return self.model_dump(include={"name", "metadata", "content"}, exclude_none=True)

    @classmethod
    def from_dict(cls, document: Dict[str, Any]) -> "Document":
        """Returns a Document object from a dictionary representation"""

        return cls.model_validate(**document)

    @classmethod
    def from_json(cls, document: str) -> "Document":
        """Returns a Document object from a json string representation"""

        return cls.model_validate_json(document)


class APITestingVectorDB(ABC):
    """Base class for Vector Databases"""

    @abstractmethod
    def create(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def doc_exists(self, document: Document) -> bool:
        raise NotImplementedError

    @abstractmethod
    def name_exists(self, name: str) -> bool:
        raise NotImplementedError

    def id_exists(self, id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def insert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        raise NotImplementedError

    def upsert_available(self) -> bool:
        return False

    @abstractmethod
    def upsert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        raise NotImplementedError

    def vector_search(self, query: str, limit: int = 5) -> List[Document]:
        raise NotImplementedError

    def keyword_search(self, query: str, limit: int = 5) -> List[Document]:
        raise NotImplementedError

    def hybrid_search(self, query: str, limit: int = 5) -> List[Document]:
        raise NotImplementedError

    @abstractmethod
    def drop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self) -> bool:
        raise NotImplementedError

    def optimize(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self) -> bool:
        raise NotImplementedError
