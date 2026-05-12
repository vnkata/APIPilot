import json
from pathlib import Path
from typing import Any, Dict, Optional

from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner
from api_testing.models.specification_model import ItemProperties
from api_testing.prompts.constraint_arbitration import ConstraintArbitration
from api_testing.utils import flatten_json_schema
from api_testing.utils import flatten_json_schema

from .static_constraint_miner import (
    StaticConstraintMiner
)

__all__ = [
    "OperationGraph",
    "OperationNode",
    "OperationEdge"
]

class ConstraintMiner:
    MAIN_CACHE = "constraint_miner.json"
    def __init__(
        self,
        spec_parser: Any,
        model: Optional[Any] = None,
        embedding_model: Optional[Any] = None,
        cache_dir: Optional[str] = None
    ) -> None:
        self.spec_parser = spec_parser
        self.model = model
        self.embedder = embedding_model
        self.project_dir = cache_dir
        self.staic_miner = StaticConstraintMiner(
            spec_parser=self.spec_parser,
            model=self.model,
            embedding_model=self.embedder,
            cache_dir=self.project_dir
        )
        self.dynamic_miner = DynamicConstraintMiner(
            spec_parser=self.spec_parser,
            model=self.model,
            cache_dir=self.project_dir
        )
        self.operations = self.spec_parser.operations

        self.arbitration = ConstraintArbitration(llm=self.model)
    def static_mining(self):
        self.static_constraints = self.staic_miner.mining()
        return self.static_constraints
    
    def dynamic_mining(self):
        self.dynamic_constraints = self.dynamic_miner.mining()
        return self.dynamic_constraints
    
    @staticmethod
    def _load_json_file(filepath: Path) -> Dict[str, Any]:
        """
        Load data from JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Loaded data dictionary
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise IOError(f"Failed to load JSON from {filepath}: {str(e)}")
        
    def _save_constraints_to_cache(self) -> None:
        """Save all constraints to main cache file."""
        cache_file = Path(self.project_dir) / self.MAIN_CACHE
        self._save_json_file(cache_file, self.constraints)

    @staticmethod
    def _save_json_file(filepath: Path, data: Dict[str, Any]) -> None:
        """
        Save data to JSON file with proper encoding.
        
        Args:
            filepath: Path to save the JSON file
            data: Data to serialize
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise IOError(f"Failed to save JSON to {filepath}: {str(e)}")
        
    def constraint_arbitration(self):
        constraints = self.merge_constraints()
        # Implement your arbitration logic here
        for endpoint, props in constraints.items():
            endpoint_constraints = [] # This will hold the final constraints for this endpoint after arbitration
            for prop, details in props.items():
                spec_constraint = details.get("spec")
                runtime_constraint = details.get("runtime")
                final_constraint = details.get("final")
                # Example arbitration logic
                if final_constraint is not None:
                    continue
                    # print(f"Final constraint for {endpoint} - {prop}: {final_constraint}")
                else:
                    endpoint_constraints.append({
                        "property": prop,
                        "spec": spec_constraint,
                        "runtime": runtime_constraint
                    })
                    print(f"No clear constraint for {endpoint} - {prop}. Spec: {spec_constraint}, Runtime: {runtime_constraint}")
            if len(endpoint_constraints) == 0:
                continue
            print(f"Arbitrating constraints for endpoint: {endpoint}")
            operation = self.operations.get(endpoint)
            if operation.successful_responses:
                flatten_responses = flatten_json_schema(operation.successful_responses.to_dict())
                data = []
                for idx, constraint in enumerate(endpoint_constraints, start=1):
                    data.append(f"#{idx}. \n Property: {constraint['property']}\n   - Spec Constraint: {constraint['spec']}\n   - Runtime Constraint: {constraint['runtime']}")

                params = {
                    "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}" if operation else endpoint,
                    "summary": operation.summary or operation.description or "",
                    "parameters": "\n".join([
                        f"- {k} : {v.to_human_readable()}"
                        for k, v in operation.parameters.items()
                    ]),
                    "responses": "\n".join([
                        f"- {k.replace('[]', '')} : {ItemProperties.from_dict(v).to_human_readable()}"
                        for k, v in flatten_responses.items()
                    ]),
                    "constraints": "\n".join(data)
                }
                data = self.arbitration.exec(**params)
                for item in data:
                    property = endpoint_constraints[item.id - 1]['property']
                    if item.answer == 1:
                        final = endpoint_constraints[item.id - 1]['spec']
                    elif item.answer == 2:
                        final = endpoint_constraints[item.id - 1]['runtime']
                    self.constraints[endpoint][property]['final'] = final
        self._save_constraints_to_cache()

    def merge_constraints(self):
        merged = {}

        for endpoint in set(self.static_constraints) | set(self.dynamic_constraints):
            d1 = self.static_constraints.get(endpoint, {})
            d2 = self.dynamic_constraints.get(endpoint, {})

            merged[endpoint] = {}

            for prop in set(d1) | set(d2):
                spec = d1.get(prop)
                runtime = d2.get(prop)
                # final logic
                if spec is None and runtime is not None:
                    final = runtime
                elif runtime is None and spec is not None:
                    final = spec
                else:
                    final = None
                merged[endpoint][prop] = {
                    "spec": spec,
                    "runtime": runtime,
                    "final":  final
                }
        self.constraints = merged
        self._save_constraints_to_cache()

        return merged
