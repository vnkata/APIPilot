from api_testing import APITesting, GeminiModel
import os
import time

from api_testing.memory.vectordb.qdrantdb import QdrantDB
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel
from api_testing.models.embedding_models.ollama_embedding_model import OllamaEmbeddingModel
from dotenv import load_dotenv

from api_testing.models.llms.azure_open_model import AzureOpenAIModel

load_dotenv()

print("============= API Testing =============")
start_time = time.perf_counter()

# llm = GeminiModel(
#     model_name="gemini-2.5-flash",
#     api_key="xx",
#     temperature=0.7,
# )
# 
llm = AzureOpenAIModel(
    model=os.getenv("AZURE_OPENAI_DEPLOYMENT") or "gpt-4.1-mini",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
    temperature=0.7,
)

embedder = HuggingfaceEmbeddingModel(  
    model="google/embeddinggemma-300m", use_half=False)


# db = QdrantDB(
#     collection="GitLab_Qwen3Embedding06B",
#     path="./.cache/GitLab Branch API",
#     host="host.docker.internal",
#     port=6333,
#     api_key="123456789",
#     embedder=embedder
# )

test = APITesting(
    "http://localhost:30000/api/v4",
    model=llm,
    # vector_db=db,
    embedder=embedder,
    spec_path="datasets\\GitLabIssues.json",
)
test.run_tests(
    num_generations=1,
    num_test_cases=20,
    mutation_ratio=0.5,
    async_mode=True,
    max_request_workers=10,  
    async_max_concurrent=20  # Only this matters for async mode
)

elapsed = time.perf_counter() - start_time
print(f"\n========================================")
print(f"Total execution time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
print(f"========================================")