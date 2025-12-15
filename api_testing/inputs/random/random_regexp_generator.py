import random
import logging
from typing import Optional
from pydantic import Field
from . import RandomGenerator

try:
    import rstr
except ImportError:
    raise ImportError("Please install the 'rstr' package: pip install rstr")

logger = logging.getLogger(__name__)


class RandomRegExpGenerator(RandomGenerator):
    """Generates random strings that match a given regular expression."""

    reg_exp: str
    min_length: Optional[int] = Field(default=-1)
    max_length: Optional[int] = Field(default=-1)
    
    def __init__(self, reg_exp=None, min_length=-1, max_length=-1, *args, **kwargs):
        self.reg_exp = reg_exp
        self.min_length = min_length
        self.max_length = max_length

        super().__init__(*args, **kwargs)


    def next_value(self) -> str:
        """Generate a random string matching the regex."""
        value = None
        try:
            # rstr.xeger ignores length limits, so we post-filter by length if needed
            for _ in range(100):  # avoid infinite loops
                candidate = rstr.xeger(self.reg_exp)
                if (
                    (self.min_length == -1 or len(candidate) >= self.min_length)
                    and (self.max_length == -1 or len(candidate) <= self.max_length)
                ):
                    value = candidate
                    break
            if value is None:
                # fallback: generate anyway
                value = rstr.xeger(self.reg_exp)
        except Exception as e:
            logger.error(f"Error generating string for regex {self.reg_exp}", exc_info=e)
            value = ""
        return value

    def next_value_as_string(self) -> str:
        return self.next_value()

    def set_min_length(self, min_length: int):
        self.min_length = min_length

    def set_max_length(self, max_length: int):
        self.max_length = max_length

    def set_seed(self, seed: int):
        """Override to reset both self and local RNG seed."""
        super().set_seed(seed)
        self._random.seed(seed)
