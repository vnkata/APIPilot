import random
from typing import Generic, List, TypeVar, Any
from pydantic import Field
from .random_generator import RandomGenerator

T = TypeVar("T")


class RandomInputValueIterator(RandomGenerator, Generic[T]):
    """Random iterator for a list of input values of type <T>."""

    values: List[T] = Field(default_factory=list)
    min_values: int = 1
    max_values: int = 1
    separator: str = ","

    def model_post_init(self, __context):
        super().model_post_init(__context)
        self._random = random.Random(self.seed)  # independent RNG

    def next_value(self) -> Any:
        """Return one or more randomly selected values from the list."""
        if not self.values:
            return None

        # Case 1: single value
        if self.min_values == 1 and self.max_values == 1:
            idx = self.rand.randint(0, len(self.values) - 1)
            return self.values[idx]

        # Case 2: random subset of values
        selected_values = []
        local_values = list(self.values)
        num_values = 0
        d = self._random.random()

        while (self.min_values > num_values) or (
            self.max_values > num_values and d < 0.5
        ):
            if not local_values:
                break  # no more values to pick
            idx = self.rand.randint(0, len(local_values) - 1)
            value_to_add = local_values.pop(idx)
            selected_values.append(value_to_add)
            num_values += 1
            d = self._random.random()

        return selected_values

    def next_value_as_string(self) -> str:
        """Return random value(s) as string."""
        value = self.next_value()
        if isinstance(value, list):
            return self.separator.join(map(str, value))
        elif value is None:
            return ""
        return str(value)
