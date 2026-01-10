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
    description: str = """
    Generates random text according to the specified mode.
    Attributes:
        mode (str): Generation mode — can be "word", "sentence", "paragraph", or "regex".
        pattern (str): Regular expression pattern used when mode is "regex".
        count (int): Number of words, sentences, or paragraphs to generate based on the mode.
        seed (int | None): Optional random seed value to ensure reproducible results.
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
    def next_fuzz_value(self, strategy: str = "injection") -> str:
        if strategy == "boundary":
            # Empty string or an extremely long string
            return self.rand.choice(["", "A" * 10000])
        
        if strategy == "injection":
            # Common SQL, XSS, or Command injections
            injections = [
                "' OR '1'='1", 
                "<script>alert(1)</script>", 
                "../../etc/passwd",
                "%; stop"
            ]
            return self.rand.choice(injections)
        
        if strategy == "encoding":
            # Non-UTF8 or special control characters
            return "\0\n\r\t\b"
            
        return ""