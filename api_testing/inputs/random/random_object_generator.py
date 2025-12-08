import json
import logging
from typing import Any, List
from pydantic import Field
from .random_generator import RandomGenerator

logger = logging.getLogger(__name__)


class RandomObjectGenerator(RandomGenerator):
    """Given a list of objects, randomly returns one of them."""

    values: List[Any] = Field(default_factory=list)

    def model_post_init(self, __context):
        super().model_post_init(__context)

    def next_value(self) -> Any:
        """Return a randomly selected object from the list."""
        if not self.values:
            return None
        idx = self.rand.randint(0, len(self.values) - 1)
        return self.values[idx]

    def next_value_as_string(self) -> str:
        """Return the randomly selected object serialized as JSON."""
        value = self.next_value()
        try:
            return json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error("Error serializing object to JSON", exc_info=e)
            # Fallback to string representation
            return str(value)
