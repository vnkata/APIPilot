from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner
from api_testing.constraint.static_constraint_miner import StaticConstraintMiner
from api_testing.dataset.specification_parser import SpecificationParser
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel
from api_testing.models.llms.gemini_model import GeminiModel


llm = GeminiModel(model_name="gemini-2.5-flash",temperature=0, api_key="...")
spec = SpecificationParser(spec_path="datasets/Bills-api.json")
spec.parse_specification()
miner = DynamicConstraintMiner(
    spec_parser=spec,
    model=llm,
    cache_dir=".cache/.cache_gpt/Bills API_1"
)
miner.extract_decls_classes()

miner.extract_dtraces()
