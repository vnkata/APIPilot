from typing import Any, Literal
from faker import Faker

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator

class RandomLocaleGenerator(RandomGenerator):
    """
    A generator that produces valid localization and regional data.

    Attributes:
        mode (str): The type of locale data to generate 
            ('language_code', 'country_code', 'locale', 'timezone', 'currency_code').
    """
    description: str = """A generator that produces valid localization and regional data.
    Params:
        mode (str): The type of locale data ('language_code', 'country_code', 'locale', 'timezone', 'currency_code').
    Output:
        str: The generated locale-specific identifier.
    """

    def __init__(
        self,
        mode: Literal["language_code", "country_code", "locale", "timezone", "currency_code"] = "locale",
        seed: int | None = None
    ):
        super().__init__(seed)
        self.mode = mode.lower()
        self.fake = Faker()

    def next_value(self, context_pool=None, *args, **kwargs) -> tuple[str, bytes, str]:
        """Generate the next valid locale value based on the selected mode."""
        mode_map = {
            "language_code": self.fake.language_code, # e.g., 'en', 'vi'
            "country_code": self.fake.country_code,   # e.g., 'US', 'VN'
            "locale": self.fake.locale,               # e.g., 'en_US', 'vi_VN'
            "timezone": self.fake.timezone,           # e.g., 'Asia/Ho_Chi_Minh'
            "currency_code": self.fake.currency_code, # e.g., 'USD', 'VND'
        }

        if self.mode not in mode_map:
            raise ValueError(f"Unsupported locale mode: {self.mode}")
            
        return mode_map[self.mode]()
    # --------------------------
    # Fuzzing
    # --------------------------
    def next_fuzz_value(
        self,
        strategy: FuzzStrategy | None,
        context_pool=None,
        *args,
        **kwargs,
    ) -> Any:
        return self.next_value(*args, **kwargs)