import random
from pydantic import Field
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

    def next_value(self) -> bool:
        """Generate a random boolean based on true_probability."""
        return self.rand.random() <= self.true_probability

    def next_value_as_string(self) -> str:
        """Return next random value as string."""
        return str(self.next_value())
