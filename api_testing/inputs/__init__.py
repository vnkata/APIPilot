import random
from abc import ABC, abstractmethod

from api_testing.inputs.file_source_generator import FileSourceGenerator
from api_testing.inputs.file_source_generator import FileSourceGenerator
from api_testing.inputs.llm_generator import LLMGenerator
from api_testing.inputs.producer_generator import ProducerGenerator
from api_testing.inputs.random_color_generator import RandomColorGenerator
from api_testing.inputs.random_credit_card_generator import RandomCreditCardGenerator
from api_testing.inputs.random_locale_generator import RandomLocaleGenerator
from api_testing.inputs.random_network_generator import RandomNetworkGenerator
from .random_boolean_generator import RandomBooleanGenerator
from .random_date_generator import RandomDateGenerator
from .random_number_generator import RandomNumberGenerator
from .random_generator import RandomGenerator
from .random_file_generator import RandomFileGenerator
from .random_text_generator import RandomTextGenerator
from .random_identity_generator import RandomIdentityGenerator
from .random_input_generator import RandomInputGenerator

class RandomGeneratorFactory:
    _registries = {
        "RandomBooleanGenerator": RandomBooleanGenerator,
        "RandomNumberGenerator": RandomNumberGenerator,
        "RandomDateGenerator": RandomDateGenerator,
        "RandomFileGenerator": RandomFileGenerator,
        "RandomTextGenerator": RandomTextGenerator,
        # "RandomIdentityGenerator": RandomIdentityGenerator,
        "RandomInputGenerator": RandomInputGenerator,
        "FileSourceGenerator": FileSourceGenerator,
        "RandomLocaleGenerator": RandomLocaleGenerator,
        "RandomColorGenerator": RandomColorGenerator,
        "RandomCreditCardGenerator": RandomCreditCardGenerator,
        "RandomNetworkGenerator": RandomNetworkGenerator,
        "LLMGenerator": LLMGenerator, ## auto fallbackn
        "ProducerGenerator": ProducerGenerator ## auto fallback
    }

    @classmethod
    def create(cls, generator_type: str, **kwargs) -> RandomGenerator:
        if generator_type not in cls._registries:
            raise ValueError(f"Unknown generator type: {generator_type}")
        return cls._registries[generator_type](**kwargs)

    def gen_description(self):
        descriptions = {}
        for registry, registry_fns in self._registries.items() :
            if registry not in ("ProducerGenerator"):
                descriptions[registry] = registry_fns.description
        return descriptions