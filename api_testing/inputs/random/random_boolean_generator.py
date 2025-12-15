import random
from pydantic import Field
from . import RandomGenerator

class RandomBooleanGenerator(RandomGenerator):
    """Random Boolean generator with configurable true probability."""

    true_probability: float = 0.5 

    def __init__(self, true_probability=0.5, *args, **kwargs):
        self.true_probability = true_probability
        super().__init__(*args, **kwargs)

    def next_value(self) -> bool:
        """Generate a random boolean based on true_probability."""
        return self.rand.random() <= self.true_probability

    def next_value_as_string(self) -> str:
        """Return next random value as string."""
        return str(self.next_value())
