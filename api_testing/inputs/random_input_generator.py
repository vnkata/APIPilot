from typing import Any, List
from .random_generator import RandomGenerator

class RandomInputGenerator(RandomGenerator):
    """
    A generator that randomly selects one or more values from a provided list.

    Attributes:
        values (List[Any]): The list of possible values to select from.
        count (int): Number of values to select (default: 1).
    """
    description: str = """A generator that randomly selects one or more values from a provided list.
    Attributes:
        values (List[Any]): The list of possible values to select from.
        count (int): Number of values to select (default: 1).
    """

    def __init__(self, values: List[Any], count: int = 1, seed: int | None = None):
        super().__init__(seed)
        self.values = values
        self.count = count

    def next_value(self) -> Any:
        if not self.values:
            return None
        if self.count <= 1:
            return self.rand.choice(self.values)
        return self.rand.sample(self.values, min(self.count, len(self.values)))
    def next_fuzz_value(self, strategy: str = "mutate") -> Any:
        """
        Generates an invalid or boundary value based on the input list.

        Strategies:
            'mutate': Picks a value from the list and breaks its data (e.g., adding null bytes).
            'empty': Returns None, an empty string, or an empty list.
            'out_of_bounds': Returns a value that is definitely not in the provided list.
            'structure': Returns a single value when a list is expected, or vice versa.
        """
        if not self.values:
            return self.rand.choice([None, "", "null"])

        if strategy == "empty":
            return self.rand.choice([None, "", [], {}])

        if strategy == "out_of_bounds":
            # Generate a string/number that is guaranteed not to be in the set
            return f"not_in_list_{self.rand.getrandbits(32)}"

        if strategy == "structure":
            # If the generator usually returns multiple items, return a single one (or vice versa)
            val = self.rand.choice(self.values)
            return [val] if self.count <= 1 else val

        # Default strategy: 'mutate'
        # Get a legitimate value and destroy it
        val = self.rand.choice(self.values)
        
        if isinstance(val, str):
            return val + "\0"
        if isinstance(val, (int, float)):
            return val * -1000000
        if isinstance(val, list):
            return val + [None, "fuzz"]
        
        return self.rand.choice([None, "undefined", "NaN"])