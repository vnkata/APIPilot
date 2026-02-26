import random
from typing import Any
from pydantic import Field

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator

class RandomBooleanGenerator(RandomGenerator):
    """
    Generates random booleans with a configurable probability of being True.
    Attributes:
        true_probability (float): Likelihood of returning True (0.0 to 1.0).
    """

    true_probability: float = 0.5 
    description: str = """Generates random boolean values"""
    def __init__(self, true_probability=0.5, *args, **kwargs):
        self.true_probability = true_probability
        super().__init__(*args, **kwargs) 

    def next_value(self, *args, **kargs) -> bool:
        """Generate a random boolean based on true_probability."""
        return self.rand.random() <= self.true_probability

    def next_value_as_string(self) -> str:
        """Return next random value as string."""
        return str(self.next_value())
    def next_fuzz_value(self) -> Any:
        """Randomly selects from specific supported strategies and returns a fuzzed value."""
        
        # Explicitly list only the strategies handled by this specific function
        supported_strategies = [
            FuzzStrategy.EMPTY,
            FuzzStrategy.TYPE_ERROR,
            FuzzStrategy.STRUCTURE,
            FuzzStrategy.MUTATE
        ]
        
        # Pick one at random
        strategy = self.rand.choice(supported_strategies)

        if strategy == FuzzStrategy.EMPTY:
            return self.rand.choice([None, ""])

        if strategy == FuzzStrategy.TYPE_ERROR:
            return self.rand.choice(["true", "false", "TRUE", "FALSE", 0, 1, "yes", "no"])

        if strategy == FuzzStrategy.STRUCTURE:
            val = self.next_value()
            return [val] if self.rand.random() > 0.5 else {"val": val}

        if strategy == FuzzStrategy.MUTATE:
            return self.rand.choice([None, "null", "undefined", -1, 2])
        
        return None