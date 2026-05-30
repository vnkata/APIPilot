from dotenv import load_dotenv
from pathlib import Path
import json

from api_testing.config.config_loader import load_config, build_llm
from api_testing.dataset import SpecificationParser
from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner

load_dotenv()

cache_dir = Path(r".cache\Bills API_3")
config = load_config("configurations.toml")
model = build_llm(config)

spec = SpecificationParser(spec_path=r"datasets\Bills-api.json")
spec.load_or_initialize(cache_dir=str(cache_dir))

miner = DynamicConstraintMiner(
    spec_parser=spec,
    model=model,
    cache_dir=str(cache_dir),
)

dynamic_constraints = miner.mining()

print(json.dumps(dynamic_constraints, indent=2, ensure_ascii=False))
print("Saved to:", cache_dir / "dynamic_constraint_miner.json")
