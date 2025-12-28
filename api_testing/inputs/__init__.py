import random
from abc import ABC, abstractmethod

from api_testing.inputs.llm_generator import LLMGenerator
from api_testing.inputs.producer_generator import ProducerGenerator
from .random_boolean_generator import RandomBooleanGenerator
from .random_date_generator import RandomDateGenerator
from .random_number_generator import RandomNumberGenerator
from .random_generator import RandomGenerator
from .random_file_generator import RandomFileGenerator
from .random_text_generator import RandomTextGenerator

class RandomGeneratorFactory:
    _registries = {
        "RandomBooleanGenerator": RandomBooleanGenerator,
        "RandomNumberGenerator": RandomNumberGenerator,
        "RandomDateGenerator": RandomDateGenerator,
        "RandomFileGenerator": RandomFileGenerator,
        "RandomTextGenerator": RandomTextGenerator,
        "LLMGenerator": LLMGenerator,
        "ProducerGenerator": ProducerGenerator
    }

    @classmethod
    def create(cls, generator_type: str, **kwargs) -> RandomGenerator:
        if generator_type not in cls._registries:
            raise ValueError(f"Unknown generator type: {generator_type}")
        return cls._registries[generator_type](**kwargs)

    def gen_description(self):
        descriptions = {}
        for registry, registry_fns in self._registries.items():
            descriptions[registry] = registry_fns.description
        return descriptions