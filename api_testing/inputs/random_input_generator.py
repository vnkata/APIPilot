from typing import Any, List
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
        return self.rand.choices(self.values, k=min(self.count, len(self.values)))
                                 
    def next_value_as_string(self) -> str:
        """Return a formatted random datetime as string."""
        value = self.next_value()
        if self.count <= 1:
            return str(value)
        return ','.join([str(v) for v in value])