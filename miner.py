from collections import defaultdict
import json
import os
from pathlib import Path
import re
import shutil


cache_dir = Path(".cache/GitLab Branch API")
log_file = Path("logs/default.log")
dst_log = cache_dir / "logs" / "gpt-5.log"

if log_file.exists():
    log_file.unlink()
    print(f"🗑️ Removed {log_file}")


from api_testing.constraint import ConstraintMiner
from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner
from api_testing.constraint.static_constraint_miner import StaticConstraintMiner
from api_testing.dataset.specification_parser import SpecificationParser
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel
from api_testing.models.llms.gemini_model import GeminiModel
from api_testing.models.llms.openai_model import OpenAIModel
from api_testing.utils.http import isSuccessful

llm = OpenAIModel(model="gpt-5", api_key=os.getenv("OPENAI_API_KEY"))

embedder = HuggingfaceEmbeddingModel()
spec = SpecificationParser(
    spec_path=str(cache_dir / "baseline_specification.json")
)
spec.parse_specification()
miner = ConstraintMiner(
    spec_parser=spec,
    model=llm,
    embedding_model=embedder,
    cache_dir=str(cache_dir),
    requestHeader={
        "PRIVATE-TOKEN": "jxQposqiCQcUtk7NNDrL"
    }
)
# miner.verify_static_constraints()

dynamic_constraints = miner.dynamic_mining()
static_constraints = miner.static_mining()

miner.constraint_arbitration()
miner.constraint_review(base_url="http://localhost:30000/api/v4", num_test_cases=30)

# Copy llm_tracker.jsonl vào cache folder
src = Path("llm_tracker.jsonl")
dst = Path(".cache/GitLab Branch API/llm_tracker.jsonl")

if src.exists():
    shutil.copy2(src, dst)
    print(f"✅ Copied {src} -> {dst}")
else:
    print(f"⚠️ Không tìm thấy {src}")
## append logfile
## append logfile
if log_file.exists():
    with open(log_file, encoding="utf-8") as src, \
         open(dst_log, "a", encoding="utf-8") as dst:
        dst.write(src.read())