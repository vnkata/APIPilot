
from abc import ABC, abstractmethod
import random


class LLMGenerator(ABC):
    description: str = "" """Using LLM Gen"""
    @abstractmethod
    def next_value(self):
        """Generate the next random value."""
        pass
    