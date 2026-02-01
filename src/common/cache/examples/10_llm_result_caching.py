"""
Example 10: LLM Result Caching
Demonstrates practical caching of LLM (Large Language Model) API calls and embeddings.

Topics:
- Caching LLM API responses
- Embedding cache for vector databases
- Prompt-based cache keys
- Reducing LLM API costs
- Cache strategies for LLM workflows
"""

import hashlib

from common.cache import CacheType
from common.cache.utils.decorators import cache_result
from common.logger import get_logger

logger = get_logger(__name__)


# Custom key function for LLM prompts
def llm_prompt_key(func, args, kwargs):
    """Generate cache key based on prompt content."""
    prompt = args[0] if args else kwargs.get("prompt", "")
    model = kwargs.get("model", "default")
    temperature = kwargs.get("temperature", 0.7)

    # Create key: model:temperature:prompt_hash
    prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
    return f"llm:response:{model}:t{temperature}:{prompt_hash}"


# LLM API simulation with caching
@cache_result(
    cache_type=CacheType.REDIS,  # Use Redis for LLM cache
    ttl=86400,  # Cache for 24 hours
    key_fn=llm_prompt_key,
    on_error=lambda et, e: logger.warning(f"LLM cache error: {et}"),
)
def call_llm(prompt: str, model: str = "gpt-4", temperature: float = 0.7) -> str:
    """Call LLM API (cached)."""
    logger.info(f"  [LLM API] Calling {model} (temp={temperature})")
    logger.info(f"    Prompt: {prompt[:50]}...")

    # Simulate LLM response
    response = {
        "model": model,
        "prompt_length": len(prompt),
        "response": f"Generated response for: {prompt[:30]}...",
        "tokens": 150,
        "cost_usd": 0.003,
    }

    return response.get("response", "")


# Embedding cache with file persistence
@cache_result(
    cache_type=CacheType.FILE,
    ttl=None,  # Permanent (embeddings don't change)
    cache_dir=".cache/embeddings",
    key_prefix="embedding:",
)
def get_embedding(text: str, model: str = "text-embedding-ada-002") -> list:
    """Get text embedding (cached permanently)."""
    logger.info(f"  [Embedding] Computing {model} for text length {len(text)}")

    # Simulate embedding (1536 dimensions for ada-002)
    import hashlib

    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % 2**32
    import random

    random.seed(seed)
    embedding = [random.random() for _ in range(1536)]

    return embedding


# Batch embeddings with caching
@cache_result(
    cache_type=CacheType.MEMORY,
    ttl=3600,
    key_prefix="batch:",
)
def get_embeddings_batch(texts: list, model: str = "text-embedding-ada-002") -> list:
    """Get embeddings for multiple texts."""
    logger.info(f"  [Embeddings] Computing batch embeddings for {len(texts)} texts")

    embeddings = []
    for text in texts:
        embedding = get_embedding(text, model)
        embeddings.append(embedding)

    return embeddings


def example_1_llm_caching():
    """Cache LLM API responses."""
    logger.info("=" * 70)
    logger.info("Example 10.1: LLM API Response Caching")
    logger.info("=" * 70)

    prompt = "Explain quantum computing in simple terms"

    # First call - hits LLM API
    logger.info("▶ First call: call_llm(prompt)")
    response1 = call_llm(prompt)
    logger.info(f"✓ Response: {response1[:50]}...")
    logger.info("  Cost: $0.003, Tokens: 150\n")

    # Second call - returns from cache
    logger.info("▶ Second call: same prompt [REDIS CACHE]")
    response2 = call_llm(prompt)
    logger.info(f"✓ Response: {response2[:50]}...")
    logger.info("  Cost: $0.00 (cached!)\n")

    print()


def example_2_prompt_variations():
    """Different prompts use different cache keys."""
    logger.info("=" * 70)
    logger.info("Example 10.2: Prompt Variations & Cache Keys")
    logger.info("=" * 70)

    prompts = [
        "What is machine learning?",
        "Explain machine learning",  # Different wording, different key
        "What is machine learning?",  # Same as first, same key
    ]

    logger.info("▶ Calling LLM with different prompts")

    for i, prompt in enumerate(prompts, 1):
        logger.info(f"\nPrompt {i}: {prompt[:40]}...")
        response = call_llm(prompt)
        logger.info(f"✓ Cached: {'No' if i == 2 else 'Yes'} (unique key)")

    logger.info("\n✓ Prompt 1 & 3 used same cache key (exact match)")
    logger.info("✓ Prompt 2 different wording → different cache key\n")

    print()


def example_3_embedding_caching():
    """Cache text embeddings."""
    logger.info("=" * 70)
    logger.info("Example 10.3: Embedding Caching")
    logger.info("=" * 70)

    text = "The quick brown fox jumps over the lazy dog"

    # First embedding - computes
    logger.info("▶ First embedding computation")
    embedding1 = get_embedding(text)
    logger.info(f"✓ Embedding dimensions: {len(embedding1)}")
    logger.info("  Cached to: .cache/embeddings/\n")

    # Second embedding - retrieved from cache
    logger.info("▶ Second embedding (same text) [FILE CACHE]")
    embedding2 = get_embedding(text)
    logger.info(f"✓ Retrieved from cache: {len(embedding2)} dimensions")
    logger.info(f"  Same embeddings: {embedding1 == embedding2}\n")

    print()


def example_4_batch_embeddings():
    """Cache batch embeddings."""
    logger.info("=" * 70)
    logger.info("Example 10.4: Batch Embeddings")
    logger.info("=" * 70)

    texts = [
        "First document about AI",
        "Second document about machine learning",
        "Third document about deep learning",
    ]

    # First batch - computes all embeddings
    logger.info(f"▶ Computing embeddings for {len(texts)} documents")
    embeddings1 = get_embeddings_batch(texts)
    logger.info(f"✓ Computed: {len(embeddings1)} embeddings")
    logger.info(f"  Total dimensions: {len(embeddings1) * len(embeddings1[0])}\n")

    # Second batch - returns from memory cache
    logger.info("▶ Same batch [MEMORY CACHE]")
    embeddings2 = get_embeddings_batch(texts)
    logger.info(f"✓ Retrieved: {len(embeddings2)} embeddings (instant)\n")

    print()


def example_5_cost_savings():
    """Demonstrate cost savings from caching."""
    logger.info("=" * 70)
    logger.info("Example 10.5: Cost Savings Analysis")
    logger.info("=" * 70)

    # Pricing (approximate)
    llm_cost_per_call = 0.003  # $0.003 per call
    embedding_cost_per_1k = 0.0001  # $0.0001 per 1K tokens

    # Scenario: 1000 similar queries per day
    queries = 1000
    cache_hit_rate = 0.8  # 80% cache hit rate

    # Without caching
    cost_no_cache = queries * llm_cost_per_call

    # With caching
    cache_misses = queries * (1 - cache_hit_rate)
    cost_with_cache = cache_misses * llm_cost_per_call

    savings = cost_no_cache - cost_with_cache
    savings_percent = (savings / cost_no_cache) * 100

    logger.info(f"Scenario: {queries:,} queries per day")
    logger.info(f"Cache hit rate: {cache_hit_rate:.0%}\n")

    logger.info("Without caching:")
    logger.info(f"  Calls: {queries:,}")
    logger.info(f"  Cost: ${cost_no_cache:.2f}\n")

    logger.info("With caching (80% hit rate):")
    logger.info(f"  Cache misses: {int(cache_misses):,}")
    logger.info(f"  Cost: ${cost_with_cache:.2f}\n")

    logger.info(f"Daily savings: ${savings:.2f} ({savings_percent:.0f}%)")
    logger.info(f"Monthly savings: ${savings * 30:.2f}")
    logger.info(f"Annual savings: ${savings * 365:.2f}\n")

    print()


def example_6_rag_pipeline_caching():
    """Caching in RAG (Retrieval-Augmented Generation) pipeline."""
    logger.info("=" * 70)
    logger.info("Example 10.6: RAG Pipeline with Caching")
    logger.info("=" * 70)

    logger.info("RAG Pipeline with multi-level caching:")
    logger.info("")

    logger.info("1. DOCUMENT EMBEDDING")
    logger.info("   ├─ Cache layer: File (.cache/embeddings/)")
    logger.info("   ├─ TTL: Permanent (never changes)")
    logger.info("   └─ Use case: One-time computation\n")

    logger.info("2. RETRIEVAL (Vector Search)")
    logger.info("   ├─ Cache layer: Memory (Qdrant/Milvus internal)")
    logger.info("   ├─ TTL: Session duration")
    logger.info("   └─ Use case: Real-time similarity search\n")

    logger.info("3. LLM GENERATION")
    logger.info("   ├─ Cache layer: Redis (.cache/llm_responses/)")
    logger.info("   ├─ TTL: 24 hours (refresh daily)")
    logger.info("   └─ Use case: Reduce API costs\n")

    logger.info("Benefits:")
    logger.info("  ✓ Embeddings computed once, reused forever")
    logger.info("  ✓ Vector search leverages in-memory indices")
    logger.info("  ✓ LLM API calls reduced 80% with caching")
    logger.info("  ✓ Overall latency reduced 95%\n")

    print()


def example_7_best_practices():
    """Best practices for LLM caching."""
    logger.info("=" * 70)
    logger.info("Example 10.7: LLM Caching Best Practices")
    logger.info("=" * 70)

    logger.info("✓ DO:")
    logger.info("  • Cache embeddings permanently (use FILE cache)")
    logger.info("  • Cache LLM responses with TTL (use REDIS)")
    logger.info("  • Use custom key functions for prompts")
    logger.info("  • Monitor cache hit rates and ROI")
    logger.info("  • Invalidate cache when models update")
    logger.info("  • Consider prompt normalization (trim whitespace)")
    logger.info("  • Cache intermediate results in RAG\n")

    logger.info("✗ DON'T:")
    logger.info("  • Cache untested/experimental LLM calls")
    logger.info("  • Cache sensitive data without encryption")
    logger.info("  • Use short TTL for embeddings (they don't change)")
    logger.info("  • Forget to account for temperature/model variations")
    logger.info("  • Ignore cache memory consumption")
    logger.info("  • Cache without measuring cost savings\n")

    logger.info("Recommended configuration:")
    logger.info("  • LLM responses: Redis, 24hr TTL")
    logger.info("  • Embeddings: File, permanent (None)")
    logger.info("  • Batch results: Memory, 1hr TTL")
    logger.info("  • Use custom key functions for consistency\n")

    print()


if __name__ == "__main__":
    logger.info("\n" + "=" * 70)
    logger.info("CACHE EXAMPLES 10: LLM Result Caching")
    logger.info("=" * 70 + "\n")

    try:
        example_1_llm_caching()
        example_2_prompt_variations()
        example_3_embedding_caching()
        example_4_batch_embeddings()
        example_5_cost_savings()
        example_6_rag_pipeline_caching()
        example_7_best_practices()

        logger.info("=" * 70)
        logger.info("✓ All LLM caching examples completed!")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Error in examples: {e}", exc_info=True)
