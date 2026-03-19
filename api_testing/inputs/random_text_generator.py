import re
from typing import Any, Literal
from faker import Faker

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator
from hypothesis import strategies as st

class RandomTextGenerator(RandomGenerator):
    """
    A generator that produces random text using the 'lorem' provider from Faker.

    Attributes:
        mode (str): The type of text to generate ('word', 'sentence', 'paragraph').
        count (int): Number of items to generate.
    """
    description: str = """
    Generates random text according to the specified mode.
    Attributes:
        mode (str): Generation mode — can be "word", "sentence", "paragraph", or "regex".
        pattern (str): Regular expression pattern used when mode is "regex".
        count (int): Number of words, sentences, or paragraphs to generate based on the mode.
        seed (int | N  one): Optional random seed value to ensure reproducible results.
    """

    def __init__(
        self,
        mode: Literal["word", "sentence", "paragraph","regex"] = "sentence",
        pattern: str = None,
        count: int = 1,
        seed: int | None = None
    ):
        super().__init__(seed)
        self.mode = mode
        self.count = count
        self.pattern = pattern
        self.fake = Faker()

    def next_value(self, *args, **kargs) -> str:
        if self.mode == "word":
            return " ".join(self.fake.words(self.count))
        elif self.mode == "sentence":
            return " ".join(self.fake.sentences(self.count))
        elif self.mode == "paragraph":
            return "\n\n".join(self.fake.paragraphs(self.count))
        elif self.mode == "regex":
            rex = st.from_regex(re.compile(self.pattern,flags=re.ASCII), fullmatch=True).example()
            return rex
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")
        
    def next_fuzz_value(self, *args, **kargs) -> Any:
        return self.next_value(*args, **kargs)