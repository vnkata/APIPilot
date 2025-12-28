
from abc import ABC, abstractmethod
import random


class ProducerGenerator(ABC):
    description: str = """Using data from poll dependency"""
    @abstractmethod
    def next_value(self):
        """Generate the next random value."""
        pass
    