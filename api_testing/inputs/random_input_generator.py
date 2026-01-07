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