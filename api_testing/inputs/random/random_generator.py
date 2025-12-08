import random
from abc import ABC, abstractmethod

class RandomGenerator(ABC):
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
