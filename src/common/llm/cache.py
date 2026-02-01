"""
LLM Semantic Cache

Embedding-based caching for LLM responses.
Uses similarity matching to find cached responses for semantically similar queries.
"""

import hashlib
import json
import threading
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from common.cache import CacheFactory, CacheType
from common.logger.utils.helpers import get_logger

logger = get_logger(__name__)

# Sentence Transformers (optional for semantic cache)
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore
    np = None  # type: ignore


class CacheEntry(BaseModel):
    """A cached LLM response with metadata."""

    model_config = ConfigDict(strict=True, frozen=False)  # Allow mutation for stats

    key: str
    messages_hash: str
    response: str
    model: str
    usage: dict[str, int] = Field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for storage."""
        return {
            "key": self.key,
            "messages_hash": self.messages_hash,
            "response": self.response,
            "model": self.model,
            "usage": self.usage,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Deserialize from dict."""
        return cls(
            key=data["key"],
            messages_hash=data["messages_hash"],
            response=data["response"],
            model=data["model"],
            usage=data.get("usage", {}),
            embedding=data.get("embedding"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if isinstance(data.get("created_at"), str)
                else datetime.now()
            ),
            access_count=data.get("access_count", 0),
            last_accessed=(
                datetime.fromisoformat(data["last_accessed"])
                if isinstance(data.get("last_accessed"), str)
                else datetime.now()
            ),
        )


class LLMCache:
    """
    LLM response cache with optional semantic similarity matching.

    Features:
    - Exact match caching (hash-based)
    - Semantic similarity caching (embedding-based)
    - TTL support
    - Cache statistics
    """

    def __init__(
        self,
        *,
        cache_name: str = "llm_cache",
        cache_type: CacheType = CacheType.MEMORY,
        ttl: int = 3600,
        enable_semantic: bool = False,
        embedding_model: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.95,
        max_semantic_entries: int = 1000,
        **cache_kwargs,
    ):
        """
        Initialize LLM cache.

        Args:
            cache_name: Name for the cache instance
            cache_type: Type of underlying cache (MEMORY, REDIS, FILE)
            ttl: Time-to-live in seconds
            enable_semantic: Enable semantic similarity matching
            embedding_model: Model for generating embeddings
            similarity_threshold: Minimum similarity for semantic match (0-1)
            max_semantic_entries: Max entries for semantic index
            **cache_kwargs: Additional arguments passed to underlying cache.
                          For FILE cache type, defaults to cache_dir=".cache/llm"
                          if not explicitly provided. This directory is resolved
                          relative to project root.

        Note:
            When using FILE cache type, cache files are stored in `.cache/llm/`
            subdirectory by default (resolved to project root). You can override
            this by passing `cache_dir` in `cache_kwargs`.
        """
        self.ttl = ttl
        self.enable_semantic = enable_semantic and EMBEDDINGS_AVAILABLE
        self.similarity_threshold = similarity_threshold
        self.max_semantic_entries = max_semantic_entries

        # Set default cache directory for FILE cache type if not provided
        if cache_type == CacheType.FILE and "cache_dir" not in cache_kwargs:
            cache_kwargs["cache_dir"] = ".cache/llm"

        # Initialize underlying cache
        self._cache = CacheFactory.get_cache(
            name=cache_name,
            cache_type=cache_type,
            **cache_kwargs,
        )

        # Initialize embedding model for semantic cache
        self._embedding_model = None
        self._embeddings_index: dict[str, list[float]] = {}
        self._index_lock = threading.Lock()

        if self.enable_semantic:
            self._init_embedding_model(embedding_model)

        logger.info(
            f"LLM cache initialized: type={cache_type.value}, "
            f"semantic={self.enable_semantic}, ttl={ttl}s"
        )

    def _init_embedding_model(self, model_name: str) -> None:
        """Initialize the embedding model."""
        try:
            self._embedding_model = SentenceTransformer(model_name)
            logger.info(f"Semantic cache enabled with model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {e}")
            self.enable_semantic = False

    def _generate_hash(self, messages: list[dict[str, Any]], model: str) -> str:
        """Generate hash key from messages and model."""
        content = json.dumps({"messages": messages, "model": model}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _generate_embedding(self, messages: list[dict[str, Any]]) -> list[float] | None:
        """Generate embedding for messages."""
        if not self._embedding_model:
            return None

        try:
            # Concatenate message contents for embedding
            text = " ".join(
                msg.get("content", "") for msg in messages if msg.get("content")
            )
            embedding = self._embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.debug(f"Failed to generate embedding: {e}")
            return None

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not np:
            return 0.0
        a_np = np.array(a)
        b_np = np.array(b)
        dot = np.dot(a_np, b_np)
        norm_a = np.linalg.norm(a_np)
        norm_b = np.linalg.norm(b_np)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    def _find_semantic_match(
        self,
        embedding: list[float],
        model: str,
    ) -> CacheEntry | None:
        """Find semantically similar cached entry."""
        if not self.enable_semantic or not embedding:
            return None

        best_match: CacheEntry | None = None
        best_similarity = 0.0

        with self._index_lock:
            for cache_key, stored_embedding in list(self._embeddings_index.items()):
                similarity = self._cosine_similarity(embedding, stored_embedding)
                if (
                    similarity > best_similarity
                    and similarity >= self.similarity_threshold
                ):
                    # Verify entry still exists and model matches
                    entry_data = self._cache.get(cache_key)
                    if entry_data:
                        entry = CacheEntry.from_dict(entry_data)
                        if entry.model == model:
                            best_similarity = similarity
                            best_match = entry

        if best_match:
            logger.debug(
                f"Semantic cache hit: similarity={best_similarity:.3f}, "
                f"key={best_match.key}"
            )

        return best_match

    def get(
        self,
        messages: list[dict[str, Any]],
        model: str,
    ) -> CacheEntry | None:
        """
        Get cached response for messages.

        Tries exact match first, then semantic similarity.

        Args:
            messages: Chat messages
            model: Model identifier

        Returns:
            CacheEntry if found, None otherwise
        """
        # Try exact match first
        cache_key = self._generate_hash(messages, model)
        entry_data = self._cache.get(cache_key)

        if entry_data:
            entry = CacheEntry.from_dict(entry_data)
            # Update access stats
            entry.access_count += 1
            entry.last_accessed = datetime.now()
            self._cache.set(cache_key, entry.to_dict(), self.ttl)
            logger.debug(f"Exact cache hit: key={cache_key}")
            return entry

        # Try semantic match
        if self.enable_semantic:
            embedding = self._generate_embedding(messages)
            if embedding:
                semantic_match = self._find_semantic_match(embedding, model)
                if semantic_match:
                    # Update access stats
                    semantic_match.access_count += 1
                    semantic_match.last_accessed = datetime.now()
                    self._cache.set(
                        semantic_match.key,
                        semantic_match.to_dict(),
                        self.ttl,
                    )
                    return semantic_match

        return None

    def set(
        self,
        messages: list[dict[str, Any]],
        model: str,
        response: str,
        usage: dict[str, int] | None = None,
    ) -> str:
        """
        Cache a response.

        Args:
            messages: Chat messages (prompt)
            model: Model identifier
            response: Response content
            usage: Token usage stats

        Returns:
            Cache key
        """
        cache_key = self._generate_hash(messages, model)

        # Generate embedding for semantic cache
        embedding = None
        if self.enable_semantic:
            embedding = self._generate_embedding(messages)
            if embedding:
                with self._index_lock:
                    # Maintain max size
                    if len(self._embeddings_index) >= self.max_semantic_entries:
                        # Remove oldest entry
                        oldest_key = next(iter(self._embeddings_index))
                        del self._embeddings_index[oldest_key]
                    self._embeddings_index[cache_key] = embedding

        entry = CacheEntry(
            key=cache_key,
            messages_hash=cache_key,
            response=response,
            model=model,
            usage=usage or {},
            embedding=embedding,
        )

        self._cache.set(cache_key, entry.to_dict(), self.ttl)
        logger.debug(f"Cached response: key={cache_key}, model={model}")

        return cache_key

    def invalidate(self, cache_key: str) -> bool:
        """Remove a specific cache entry."""
        with self._index_lock:
            if cache_key in self._embeddings_index:
                del self._embeddings_index[cache_key]
        return self._cache.delete(cache_key)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._index_lock:
            self._embeddings_index.clear()
        self._cache.clear()
        logger.info("LLM cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        base_stats = self._cache.get_stats()
        return {
            "hits": base_stats.hits,
            "misses": base_stats.misses,
            "hit_rate": base_stats.get_hit_rate(),
            "size": self._cache.get_size(),
            "semantic_enabled": self.enable_semantic,
            "semantic_index_size": len(self._embeddings_index),
            "similarity_threshold": self.similarity_threshold,
            "ttl": self.ttl,
        }


# Global cache instance (lazy initialization)
_global_cache: LLMCache | None = None


def get_llm_cache(
    *,
    cache_name: str = "llm_cache",
    cache_type: CacheType = CacheType.FILE,
    ttl: int = 3600,
    enable_semantic: bool = False,
    **kwargs,
) -> LLMCache:
    """
    Get or create the global LLM cache.

    Args:
        cache_name: Name for the cache instance
        cache_type: Type of underlying cache (default: FILE)
        ttl: Time-to-live in seconds (default: 3600)
        enable_semantic: Enable semantic similarity matching (default: False)
        **kwargs: Additional arguments passed to LLMCache constructor.
                 For FILE cache type, cache_dir defaults to ".cache/llm"
                 if not explicitly provided.

    Returns:
        Global LLMCache instance

    Note:
        When using FILE cache type (default), cache files are stored in
        `.cache/llm/` subdirectory relative to project root. You can override
        this by passing `cache_dir` in kwargs.
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMCache(
            cache_name=cache_name,
            cache_type=cache_type,
            ttl=ttl,
            enable_semantic=enable_semantic,
            **kwargs,
        )
    return _global_cache


def reset_llm_cache() -> None:
    """Reset the global LLM cache (mainly for testing)."""
    global _global_cache
    if _global_cache:
        _global_cache.clear()
    _global_cache = None


__all__ = [
    "LLMCache",
    "CacheEntry",
    "get_llm_cache",
    "reset_llm_cache",
    "EMBEDDINGS_AVAILABLE",
]
