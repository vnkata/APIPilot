
from abc import ABC, abstractmethod
import random

from api_testing.inputs.fuzz_strategy import FuzzStrategy


class RandomGenerator(ABC):
    description: str = ""
    """Superclass for random generators with seed management."""

    def __init__(self, seed: int | None = None):
        self.rand = random.Random()
        self.seed = seed if seed is not None else random.getrandbits(64)
        self.rand.seed(self.seed)

    def set_seed(self, seed: int):
        self.seed = seed
        self.rand.seed(seed)

    def get_seed(self) -> int:
        return self.seed

    @abstractmethod
    def next_value(self):
        """Generate the next random value."""
        pass
    @abstractmethod
    def next_fuzz_value(self, strategy: FuzzStrategy):
        """Generate the next fuzzed value."""
        pass
    