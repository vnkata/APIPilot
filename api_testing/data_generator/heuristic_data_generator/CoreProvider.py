from typing import Optional, Sequence, Tuple, Union, Any
from faker import Faker

from api_testing.data_generator.heuristic_data_generator.BaseProvider import BaseProvider

class CoreProvider(BaseProvider): # Inheriting from BaseProvider for get_report
    def __init__(self, faker_instance: Faker):
        self.fake = faker_instance

    def random_number(self, min_val: float = 0, max_val: float = 100, num_type: str = 'integer') -> Union[int, float]:
        """
        Generates a random numeric value within a specific range.
        
        :param min_val: Lower bound of the range.
        :param max_val: Upper bound of the range.
        :param num_type: Type of number to generate ('integer' or 'float').
        :return: A random number.
        """
        if num_type == 'float':
            return round(self.fake.random.uniform(float(min_val), float(max_val)), 2)
        return self.fake.random_int(min=int(min_val), max=int(max_val))

    def random_input_value(self, values: list, count: int = 1) -> Any:
        """
        Picks one or more random items from a provided list of options.
        
        :param values: List of possible values to select from.
        :param count: Number of items to select from the list.
        :return: A single value or a list of values.
        """
        if not values: 
            return None
        if count <= 1: 
            return self.fake.random_element(values)
        return self.fake.random_elements(elements=values, length=count)

    def image(
        self,
        size: Tuple[int, int] = (256, 256),
        image_format: str = "png",
        hue: Union[int, Sequence[int], str, None] = None,
        luminosity: Optional[str] = None,
    ) -> bytes:
        """
        Generates a physical image file and returns its raw binary data.
        Useful for testing multipart/form-data file uploads.

        :param size: Image dimensions in pixels (width, height).
        :param image_format: Extension format like 'png', 'jpeg', or 'gif'.
        :param hue: Color range (monochrome, red, orange, yellow, green, blue, purple, pink).
        :param luminosity: Brightness level (bright, dark, light, random).
        :return: Image bytes.
        """
        try:
            return self.fake.image(
                size=size,
                image_format=image_format,
                hue=hue,
                luminosity=luminosity,
            )
        except Exception as e:
            # Error handling for missing dependencies like Pillow
            raise RuntimeError(f"Failed to generate image bytes: {e}")

    def image_url(
        self, 
        width: Optional[int] = None, 
        height: Optional[int] = None, 
        placeholder_url: Optional[str] = None
    ) -> str:
        """
        Generates a URL string pointing to a placeholder image.
        Useful for testing fields that store links rather than actual files.

        :param width: Optional image width in pixels.
        :param height: Optional image height in pixels.
        :param placeholder_url: Custom template URL containing {width} and {height}.
        :return: A URL string.
        """
        return self.fake.image_url(
            width=width, 
            height=height, 
            placeholder_url=placeholder_url
        )
    def date_time_iso(self) -> str:
        """
        Generates a date-time string in ISO-8601 format.
        Commonly used for 'created_at' or 'updated_at' fields.

        :return: ISO-8601 formatted string (e.g., '2025-12-25T15:30:00').
        """
        return self.fake.date_time().isoformat()

    def date_between(
        self, 
        start_date: str = "-30d", 
        end_date: str = "today"
    ) -> str:
        """
        Generates a date string within a specific range.
        
        :param start_date: String indicating start (e.g., '-1y', '-30d', 'today').
        :param end_date: String indicating end.
        :return: Date string in YYYY-MM-DD format.
        """
        return self.fake.date_between(start_date=start_date, end_date=end_date).strftime("%Y-%m-%d")

    def future_date(self, end_date: str = "+30d") -> str:
        """
        Generates a date that occurs in the future.
        Useful for 'expiration_date' or 'scheduled_at' fields.

        :param end_date: How far into the future to generate (e.g., '+1y').
        :return: Date string in YYYY-MM-DD format.
        """
        return self.fake.future_date(end_date=end_date).strftime("%Y-%m-%d")

    def unix_time(self) -> int:
        """
        Generates a Unix timestamp (seconds since epoch).
        
        :return: Integer timestamp.
        """
        return self.fake.unix_time()

    def timezone(self) -> str:
        """
        Returns a random timezone name.
        Example: 'America/New_York'

        :return: Timezone string.
        """
        return self.fake.timezone()