from api_testing import APITesting
from api_testing.config.config_loader import build_embedder, build_llm, load_config
from dotenv import load_dotenv
import time

load_dotenv()

print("============= API Testing =============")
start_time = time.perf_counter()

config = load_config("configurations.toml")
llm = build_llm(config)
embedder = build_embedder(config)

test = APITesting(
    base_url=config["project"]["base_url"],
    base_title=config["project"].get("base_title") or None,
    spec_path=config["project"]["spec_path"],
    model=llm,
    embedder=embedder,
)

run = config["run"]
test.run_tests(
    num_generations=run["num_generations"],
    num_test_cases=run["num_test_cases"],
    mutation_ratio=run["mutation_ratio"],
    header_mutation_ratio=run["header_mutation_ratio"],
    async_mode=run["async_mode"],
    max_request_workers=run["max_request_workers"],
    async_max_concurrent=run["async_max_concurrent"],
    headers=config.get("headers", {}),
)

elapsed = time.perf_counter() - start_time
print("\n========================================")
print(f"Total execution time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
print("========================================")
