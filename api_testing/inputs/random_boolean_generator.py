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
    def next_fuzz_value(self, strategy: str = "type_error") -> Any:
            """
            Generates an invalid or boundary value for a boolean type.

            Strategies:
                'mutate': Returns a non-boolean representation of the current state.
                'empty': Returns null or empty values.
                'type_error': Returns common non-boolean values used to confuse parsers (strings/ints).
                'structure': Returns a list or object containing a boolean.
            """
            if strategy == "empty":
                return self.rand.choice([None, ""])

            if strategy == "type_error":
                # Values that are often incorrectly used as booleans in different languages
                return self.rand.choice(["true", "false", "TRUE", "FALSE", 0, 1, "yes", "no", "on", "off"])

            if strategy == "structure":
                val = self.next_value()
                return [val] if self.rand.random() > 0.5 else {"val": val}

            # Default strategy: 'mutate'
            # Returns values that break the strict boolean primitive expectation
            return self.rand.choice([None, "null", "undefined", -1, 2])