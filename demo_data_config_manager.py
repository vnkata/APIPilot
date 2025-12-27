import json
from pathlib import Path
from dataclasses import asdict
from prance import ResolvingParser

from api_testing.data_generator.data_config_manager.data_config_manager import DataConfigManager
from api_testing.data_generator.heuristic_data_generator.HeuristicGenerator import HeuristicDataGenerator


# Import your classes here
# from your_module import DataBlueprintManager, HeuristicDataGenerator

def main():
    # 1. Setup Paths
    spec_path = Path("datasets/GitLabIssues.json")
    output_config_path = Path("Test/gitlab_blueprint.json")
    if not output_config_path.parent.exists():
        output_config_path.parent.mkdir(parents=True, exist_ok=True)
    # 2. Initialize the Generator
    # We initialize this first because the Manager will use its inference logic
    
    # 3. Parse and Extract the Blueprint
    print(f"[*] Parsing specification: {spec_path}")
    parser = ResolvingParser(str(spec_path))

    print("[*] Extracting data blueprints...")
    blueprints = DataConfigManager.extract_on_rule_based(
        spec=parser.specification,
    )
    
    DataConfigManager.save_config_to_file(
        endpoints_config=blueprints,
        output_path=output_config_path,
    )


if __name__ == "__main__":
    main()