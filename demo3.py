from api_testing import APITesting, GeminiModel
from pathlib import Path
import os

from api_testing.memory.vectordb.qdrantdb import QdrantDB
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel
from api_testing.models.embedding_models.ollama_embedding_model import OllamaEmbeddingModel
from dotenv import load_dotenv

from api_testing import APITesting
from api_testing.models.llms.openai_model import OpenAIModel
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel

llm = GeminiModel(model_name="gemini-2.5-flash-lite",
                  temperature=0, 
)
embedder = HuggingfaceEmbeddingModel()

tester = APITesting(
  base_url="https://canada-holidays.ca",
  spec_path="datasets/CanadaHoliday.json",
  model=llm,
  embedder=embedder,
)

# Run end-to-end test generations
tester.run_tests(num_generations=2, num_test_cases=30, mutation_ratio=0.1)