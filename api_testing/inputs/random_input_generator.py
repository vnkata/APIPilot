from typing import Any, List

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator

class RandomInputGenerator(RandomGenerator):
    description: str = """A generator that randomly selects one or more values from a provided list.
    Attributes:
        values (List[Any]): The list of possible values to select from.
        count (int): Number of values to select (default: 1).
    """

    def __init__(self, values: List[Any], count: int = 1, *args, **kwargs):
        self.values = values
        self.count = count
        super().__init__(*args, **kwargs)

    def next_value(self) -> Any:
        if not self.values:
            return None
        if self.count <= 1:
            return self.rand.choice(self.values)
        return self.rand.sample(self.values, min(self.count, len(self.values)))
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