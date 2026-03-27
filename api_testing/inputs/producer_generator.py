
from abc import ABC, abstractmethod
import random
from typing import Any, List

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from api_testing.inputs.mutator import Mutator
from .random_generator import RandomGenerator


class ProducerGenerator(RandomGenerator):
    description: str = """Using data from poll dependency"""
    pool: List

    def __init__(self, pool: List = [], *args, **kwargs):
        self.pool = pool
        # self.key  = key
        super().__init__(*args, **kwargs)

    def next_value(self, context_pool=None, *args, **kargs):
        """Generate the next random value."""
        # 
        if self.pool == []:
            return None
        resource = random.choice(self.pool)
        inputs = context_pool.consume(resource["resource"])
        # if resource["key"] in context_pool.cache:
        #     return context_pool.cache.get(resource["key"])
        if len(inputs) > 0:
            value = self.rand.choice(inputs)
            context_pool.set_cache(resource["resource"], value)
            for key, nested in value.items():
                if ":" not in key:
                    continue
                _, child_entity = key.split(":", 1)
                if isinstance(nested, list):
                    for item in nested:
                        context_pool.set_cache(child_entity, item)
                elif isinstance(nested, dict):
                    context_pool.set_cache(child_entity, nested)
            return value.get(resource["key"]) 
        return None
    
    def next_fuzz_value(self, strategy: FuzzStrategy, context_pool=None, *args, **kargs) -> Any:
        val = self.next_value(context_pool=context_pool)
        mutator = Mutator()
        return mutator.mutate(val)