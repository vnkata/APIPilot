from typing import Literal
from faker import Faker
from .random_generator import RandomGenerator

class RandomColorGenerator(RandomGenerator):
    """
    A generator that produces valid color representations in various formats.

    Attributes:
        format (str): The format of the color ('hex', 'rgb', 'hsl', 'name').
    """
    description: str = """A generator that produces valid color values for UI/Theme testing.
    Params:
        format (str): The output format ('hex', 'rgb', 'hsl', 'name').
    Output:
        str: The generated color value.
    """

    def __init__(
        self,
        format: Literal["hex", "rgb", "hsl", "name"] = "hex",
        seed: int | None = None
    ):
        super().__init__(seed)
        self.format = format.lower()
        self.fake = Faker()

    def next_value(self) -> str:
        """Generate a random color in the requested format."""
        if self.format == "hex":
            return self.fake.hex_color()
        elif self.format == "rgb":
            return self.fake.rgb_color()
        elif self.format == "hsl":
            # Faker doesn't have a direct HSL provider in all versions, 
            # so we can generate components.
            h = self.rand.randint(0, 360)
            s = self.rand.randint(0, 100)
            l = self.rand.randint(0, 100)
            return f"hsl({h}, {s}%, {l}%)"
        elif self.format == "name":
            return self.fake.color_name()
        else:
            raise ValueError(f"Unsupported color format: {self.format}")

    def next_value_as_string(self) -> str:
        return self.next_value()
    def next_fuzz_value(self, strategy: str):
        pass