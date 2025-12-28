from typing import Any, Dict, Dict, List, Optional
from faker import Faker

from api_testing.data_generator.heuristic_data_generator.CoreProvider import CoreProvider
from api_testing.data_generator.heuristic_data_generator.FileProvider import FileProvider
from api_testing.data_generator.heuristic_data_generator.IdentityProvider import IdentityProvider
from api_testing.data_generator.heuristic_data_generator.LoremProvider import LoremProvider





class HeuristicDataGenerator:
    def __init__(self, seed=None):
        self.fake = Faker()
        if seed:
            Faker.seed(seed)
        
        # Register providers as both attributes and in a dictionary
        self.core = CoreProvider(self.fake)
        self.lorem = LoremProvider(self.fake)
        self.file = FileProvider(self.fake)
        self.identity = IdentityProvider(self.fake)
        self.providers = {
            "core": self.core,
            "lorem": self.lorem,
            "file": self.file,
            "identity": self.identity,
        }

    def add_provider(self, name: str, provider_instance):
        """
        Add a new provider to the generator.
        :param name: Name to reference the provider.
        :param provider_instance: An instance of the provider.
        """
        self.providers[name] = provider_instance
        setattr(self, name, provider_instance)  # Also add as attribute

    def get_report_llm(self) -> str:
        """
        Example: Combine reports from all providers that have a 'get_report' method.
        """
        report = []
        for name, provider in self.providers.items():
            if hasattr(provider, "get_report"):
                report.append(f"=== {name.capitalize()} Provider ===")
                provider_report = provider.get_report()
                report.append(str(provider_report))
        return "\n".join(report)
    
    @staticmethod
    def infer_generation_rule(
        field_type: str, 
        field_name: str, 
        enum_values: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """
        Logic moved from Manager to Generator.
        Analyzes field metadata to return a dict compatible with FieldGenerationRule.
        """
        name_lower = field_name.lower()

        # 1. Handle Enums using core
        if enum_values:
            return {
                "function": "core.random_input_value",
                "arguments": {"values": enum_values}
            }

        # 2. Date/Time Detection using core
        if any(kw in name_lower for kw in ["date", "time", "at", "timestamp"]):
            return {"function": "core.date_time_iso", "arguments": {}}

        # 3. Numeric types using core
        if field_type in ["integer", "number"]:
            return {
                "function": "core.random_number",
                "arguments": {
                    "min_val": 0, 
                    "max_val": 100, 
                    "num_type": "integer" if field_type == "integer" else "float"
                }
            }

        # 4. Booleans using core
        if field_type == "boolean":
            return {
                "function": "core.random_input_value",
                "arguments": {"values": [True, False]}
            }

        # 5. Default string fallback using lorem
        return {"function": "lorem.word", "arguments": {}}

    def generate_value_by_rule(self, function_path: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a specific provider function based on the string path (e.g., 'core.random_number').
        """
        if not function_path:
            return None
            
        try:
            provider_name, method_name = function_path.split(".")
            provider = self.providers.get(provider_name)
            
            if provider and hasattr(provider, method_name):
                method = getattr(provider, method_name)
                return method(**arguments)
        except Exception as e:
            # Comments remain in English as requested
            print(f"Error executing heuristic: {function_path} with {arguments}. Error: {e}")
            
        return None