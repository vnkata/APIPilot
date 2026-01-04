from typing import Literal
from faker import Faker
from .random_generator import RandomGenerator

class RandomTextGenerator(RandomGenerator):
    """
    A generator that produces random text using the 'lorem' provider from Faker.

    Attributes:
        mode (str): The type of text to generate ('word', 'sentence', 'paragraph').
        count (int): Number of items to generate.
    """
    description: str = """A generator that produces random text using the 'lorem' provider from Faker.
    Params:
        mode (str): The type of text to generate ('word', 'sentence', 'paragraph').
        count (int): Number of items to generate (default: 1).
    Output:
        str: The generated text.
    """

    def __init__(
        self,
        mode: Literal["word", "sentence", "paragraph"] = "sentence",
        count: int = 1,
        seed: int | None = None
    ):
        super().__init__(seed)
        self.mode = mode
        self.count = count
        self.fake = Faker()

    def next_value(self) -> str:
        if self.mode == "word":
            return " ".join(self.fake.words(self.count))
        elif self.mode == "sentence":
            return " ".join(self.fake.sentences(self.count))
        elif self.mode == "paragraph":
            return "\n\n".join(self.fake.paragraphs(self.count))
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")