import random
import string
import logging
from pydantic import Field
from .random_generator import RandomGenerator

logger = logging.getLogger(__name__)


class RandomStringGenerator(RandomGenerator):
    """Generates random strings with configurable character sets and length range."""

    min_length: int = Field(default=0)
    max_length: int = Field(default=10)
    include_alphabetic: bool = Field(default=True)
    include_numbers: bool = Field(default=False)
    include_special_characters: bool = Field(default=False)

    def model_post_init(self, __context):
        super().model_post_init(__context)

    def next_value(self) -> str:
        """Generate a random string based on current configuration."""
        string_conf = (
            4 * int(self.include_alphabetic)
            + 2 * int(self.include_numbers)
            + 1 * int(self.include_special_characters)
        )

        string_length = self.rand.randint(self.min_length, self.max_length)
        generated_string = ""

        try:
            match string_conf:
                case 7:  # Alphabetic + Numeric + Special
                    generated_string = self._random_ascii(string_length)
                case 6:  # Alphabetic + Numeric
                    generated_string = self._random_alphanumeric(string_length)
                case 4:  # Alphabetic only
                    generated_string = self._random_alpha(string_length)
                case 2:  # Numeric only
                    generated_string = self._random_numeric(string_length)
                case 0:  # Nothing included
                    generated_string = ""
                case 5 | 3 | 1:  # Mixed cases with exclusions
                    generated_string = self._complete_string(
                        self._random_ascii(string_length), string_conf
                    )
                case _:
                    raise ValueError(f"Illegal stringConf: {string_conf}")
        except Exception as e:
            logger.error(f"Error generating random string: {e}", exc_info=e)
            generated_string = ""

        return generated_string

    def next_value_as_string(self) -> str:
        return self.next_value()

    # -----------------------
    # Helper methods
    # -----------------------

    def _random_ascii(self, length: int) -> str:
        """Generate ASCII string similar to RandomStringUtils.randomAscii()."""
        return "".join(chr(self.rand.randint(32, 126)) for _ in range(length))

    def _random_alpha(self, length: int) -> str:
        """Generate alphabetic string."""
        return "".join(self.rand.choice(string.ascii_letters) for _ in range(length))

    def _random_numeric(self, length: int) -> str:
        """Generate numeric string."""
        return "".join(self.rand.choice(string.digits) for _ in range(length))

    def _random_alphanumeric(self, length: int) -> str:
        """Generate alphanumeric string."""
        chars = string.ascii_letters + string.digits
        return "".join(self.rand.choice(chars) for _ in range(length))

    def _complete_string(self, first_string: str, string_conf: int) -> str:
        """Emulate completeString() behavior by filtering character categories."""
        final_string = first_string
        while len(final_string) < self.min_length:
            final_string += self._random_ascii(self.max_length - len(final_string))

            match string_conf:
                case 5:  # Alphabetic + Special, remove digits
                    final_string = "".join(c for c in final_string if not c.isdigit())
                case 3:  # Numeric + Special, remove alphabetic
                    final_string = "".join(c for c in final_string if not c.isalpha())
                case 1:  # Special only, remove letters & digits
                    final_string = "".join(
                        c for c in final_string if not c.isalnum()
                    )
                case _:
                    raise ValueError(
                        f"Illegal stringConf for completeString: {string_conf}"
                    )
        return final_string
