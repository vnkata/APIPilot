from hashlib import md5
from typing import List, Optional, Dict, Any
from typing import Any, Dict, List, Optional, Union
from api_testing.models.base_model import APITestingBaseEmbeddingModel
from .base import Distance, Document, APITestingVectorDB

from hashlib import md5
from api_testing.log import logger
try:
    from qdrant_client import QdrantClient  # noqa: F401
    from qdrant_client.http import models
except ImportError:
    raise ImportError(
        "The `qdrant-client` package is not installed. " "Please install it via `pip install qdrant-client`.")


class QdrantDB(APITestingVectorDB):
    def __init__(
            self,
            collection: str,
            embedder: Optional[Union[str,
                                     APITestingBaseEmbeddingModel]] = None,
            distance: Distance = Distance.cosine,
            location: Optional[str] = None,
            url: Optional[str] = None,
            port: Optional[int] = 6333,
            grpc_port: int = 6334,
            prefer_grpc: bool = False,
            https: Optional[bool] = False,
            api_key: Optional[str] = None,
            prefix: Optional[str] = None,
            timeout: Optional[float] = 60,
            host: Optional[str] = None,
            path: Optional[str] = None,
            # reranker: Optional[Reranker] = None,
            **kwargs,
    ):
        # Collection attributes
        self.collection = collection
        # Embedder for embedding the document contents
        self.embedder = embedder
        self.dimensions = 1024

        # Distance metric
        self.distance = distance
        # Qdrant client instance
        self._client = None

        # Qdrant client arguments
        self.location = location
        self.url = url
        self.port = port
        self.grpc_port = grpc_port
        self.prefer_grpc = prefer_grpc
        self.https = https
        self.api_key = api_key
        self.prefix = prefix
        self.timeout = timeout
        self.host = host
        self.path = path
        # self.reranker: Optional[Reranker] = reranker
        # Qdrant client kwargs
        self.kwargs = kwargs
        #

    @property
    def client(self) -> "QdrantClient":
        if self._client is None:

            logger.debug("Creating Qdrant Client")

            self._client = QdrantClient(
                port=self.port,
                grpc_port=self.grpc_port,
                prefer_grpc=self.prefer_grpc,
                https=self.https,
                api_key=self.api_key,
                prefix=self.prefix,
                timeout=self.timeout,
                host=self.host,
                **self.kwargs,
            )
        return self._client

    def create(self) -> None:
        # Collection distance
        _distance = models.Distance.COSINE
        if self.distance == Distance.l2:
            _distance = models.Distance.EUCLID
        elif self.distance == Distance.max_inner_product:
            _distance = models.Distance.DOT

        if not self.exists():
            logger.debug(f"Creating collection: {self.collection}")
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(
                    size=self.dimensions, distance=_distance),
            )

    def doc_exists(self, document: Document) -> bool:
        """
        Validating if the document exists or not

        Args:
            document (Document): Document to validate
        """
        if self.client:
            cleaned_content = document.content.replace("\x00", "\ufffd")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            collection_points = self.client.retrieve(
                collection_name=self.collection,
                ids=[doc_id],
            )
            return len(collection_points) > 0
        return False

    def name_exists(self, name: str) -> bool:
        """
        Validates if a document with the given name exists in the collection.

        Args:
            name (str): The name of the document to check.

        Returns:
            bool: True if a document with the given name exists, False otherwise.
        """
        if self.client:
            scroll_result = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(
                        key="name", match=models.MatchValue(value=name))]
                ),
                limit=1,
            )
            return len(scroll_result[0]) > 0
        return False

    def insert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None, batch_size: int = 10) -> None:
        """
        Insert documents into the database.

        Args:
            documents (List[Document]): List of documents to insert
            filters (Optional[Dict[str, Any]]): Filters to apply while inserting documents
            batch_size (int): Batch size for inserting documents
        """
        logger.debug(f"Inserting {len(documents)} documents")
        points = []
        for document in documents:
            # document.embed(embedder=self.embedder)
            cleaned_content = document.content.replace("\x00", "\ufffd")
            doc_id = md5(cleaned_content.encode()).hexdigest()
            embedding = self.embedder.embed(cleaned_content)

            points.append(
                models.PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload={
                        "id": doc_id,
                        "name": document.name,
                        "metadata": document.metadata,
                        "content": cleaned_content,
                        # "usage": document.usage,
                    },
                )
            )
            logger.debug(
                f"Inserted document: {document.name} ({document.metadata})")
        if len(points) > 0:
            self.client.upsert(collection_name=self.collection,
                               wait=False, points=points)
        logger.debug(f"Upsert {len(points)} documents")

    def upsert(self, documents: List[Document], filters: Optional[Dict[str, Any]] = None) -> None:
        """
        Upsert documents into the database.

        Args:
            documents (List[Document]): List of documents to upsert
            filters (Optional[Dict[str, Any]]): Filters to apply while upserting
        """
        logger.debug("Redirecting the request to insert")
        self.insert(documents)

    def search(self, query: str, limit: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Search for documents in the database.

        Args:
            query (str): Query to search for
            limit (int): Number of search results to return
            filters (Optional[Dict[str, Any]]): Filters to apply while searching
        """
        query_embedding = self.embedder.embed_text(query)

        if query_embedding is None:
            logger.error(f"Error getting embedding for Query: {query}")
            return []

        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_embedding,
            with_vectors=True,
            with_payload=True,
            limit=limit,
        )

        # Build search results
        search_results: List[Document] = []
        for result in results:
            if result.payload is None:
                continue
            search_results.append(
                Document(
                    name=result.payload["name"],
                    metadata=result.payload["metadata"],
                    content=result.payload["content"],
                    embedding=result.vector,
                    score=result.score
                )
            )

        # if self.reranker:
        #     search_results = self.reranker.rerank(
        #         query=query, documents=search_results)

        return search_results

    def drop(self) -> None:
        if self.exists():
            logger.debug(f"Deleting collection: {self.collection}")
            self.client.delete_collection(self.collection)

    def exists(self) -> bool:
        if self.client:
            collections_response: models.CollectionsResponse = self.client.get_collections()
            collections: List[models.CollectionDescription] = collections_response.collections
            for collection in collections:
                if collection.name == self.collection:
                    # collection.status == models.CollectionStatus.GREEN
                    return True
        return False

    def get_count(self) -> int:
        count_result: models.CountResult = self.client.count(
            collection_name=self.collection, exact=True)
        return count_result.count

    def optimize(self) -> None:
        pass

    def delete(self) -> bool:
        return False
