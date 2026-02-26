
from abc import ABC, abstractmethod
import random
from typing import Any, List

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator


class ProducerGenerator(RandomGenerator):
    description: str = """Using data from poll dependency"""
    pool: str
    key: str

    def __init__(self, pool: str = None, key:str="", *args, **kwargs):
        self.pool = pool
        self.key  = key
        super().__init__(*args, **kwargs)

    def next_value(self, context_pool=None, *args, **kargs):
        """Generate the next random value."""
        inputs = context_pool.consume(self.pool)
        if self.key in context_pool.cache:
            return context_pool.cache.get(self.key)
        if len(inputs) > 0:
            value = self.rand.choice(inputs)
            context_pool.set_cache(value)
            return value.get(self.key)
        return None
    
    def next_fuzz_value(self, strategy: FuzzStrategy) -> Any:
        if not self.values:
            return self.rand.choice([None, "", "null"])

        if strategy == FuzzStrategy.EMPTY:
            return self.rand.choice([None, "", [], {}])

        if strategy == FuzzStrategy.OUT_OF_BOUNDS:
            return f"not_in_list_{self.rand.getrandbits(32)}"

        if strategy == FuzzStrategy.STRUCTURE:
            val = self.rand.choice(self.values)
            return [val] if self.count <= 1 else val

        if strategy == FuzzStrategy.MUTATE:
            val = self.rand.choice(self.values)
            if isinstance(val, str):
                return val + "\0"
            if isinstance(val, (int, float)):
                return val * -1000000
            if isinstance(val, list):
                return val + [None, "fuzz"]
        
        return None