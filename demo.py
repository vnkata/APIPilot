from api_testing import APITesting, GeminiModel
from pathlib import Path
import os

from api_testing.memory.vectordb.qdrantdb import QdrantDB
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel
from api_testing.models.embedding_models.ollama_embedding_model import OllamaEmbeddingModel

print("============= API Testing =============")

llm = GeminiModel(
    model_name="gemini-2.5-flash",
    # api_key="xx",
    temperature=0.7,
)
embedder = OllamaEmbeddingModel(
    base_url="http://host.docker.internal:11434",
    model_name="siv/Qwen3-Embedding-0.6B-GGUF:F16"
)

db = QdrantDB(
    collection="GitLab_Qwen3Embedding06B",
    path="./.cache/GitLab Branch API",
    host="host.docker.internal",
    port=6333,
    api_key="123456789",
    embedder=embedder
)

test = APITesting(
    "localhost:80",
    model=llm,
    vector_db=db,
    embedder=embedder,
    spec_path="datasets/CanadaHoliday.json",
)
