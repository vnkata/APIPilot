import random
from pydantic import Field
from .random_generator import RandomGenerator


class RandomBooleanGenerator(RandomGenerator):
    """Random Boolean generator with configurable true probability."""

    true_probability: float = Field(default=0.5, ge=0.0, le=1.0)

    def model_post_init(self, __context):
        # Initialize random state using the parent model’s logic
        super().model_post_init(__context)

    def next_value(self) -> bool:
        """Generate a random boolean based on true_probability."""
        return self.rand.random() <= self.true_probability

    def next_value_as_string(self) -> str:
        """Return next random value as string."""
        return str(self.next_value())
