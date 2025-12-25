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