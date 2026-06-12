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

llm = OpenAIModel(model="gpt-5", api_key=os.getenv("OPENAI_API_KEY"))

embedder = HuggingfaceEmbeddingModel()

tester = APITesting(
  base_url="http://localhost:30000/api/v4",
  spec_path="datasets/GitLabBranch.json",
  model=llm,
  embedder=embedder,
  constraint_mining=False,
  requestHeader={
    "PRIVATE-TOKEN": "jxQposqiCQcUtk7NNDrL"
  }
)
# Run end-to-end test generations
tester.run_tests(num_generations=2, num_test_cases=60, mutation_ratio=0) 