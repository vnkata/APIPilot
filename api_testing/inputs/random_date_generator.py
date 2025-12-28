import random
import logging
from datetime import datetime, timedelta
from pydantic import Field
from .random_generator import RandomGenerator

logger = logging.getLogger(__name__)


class RandomDateGenerator(RandomGenerator):
    """Random date generator with optional start/end range and formatting."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    start_days: int = 0
    end_days: int = 0
    from_today: bool = False
    format: str = Field(default="yyyy-MM-dd HH:mm:ss")
    description: str = """
    A generator that produces random date and time values.
    Attributes:
        start_date (datetime | None): Optional fixed start date for the range.
        end_date (datetime | None): Optional fixed end date for the range.
        start_days (int): Number of days offset from the start date (if applicable).
        end_days (int): Number of days offset from the end date (if applicable).
        from_today (bool): If True, generate dates relative to the current day.
        format (str): The output date format string (default: "yyyy-MM-dd HH:mm:ss")
    """
    def __init__(self, start_date=None, end_date=None, start_days=None, end_days=None, from_today=None, format=None, *args, **kwargs):
        current_date = datetime.now()
        self.start_date = start_date or current_date - timedelta(days=365 * 10) # 10 years
        self.end_date = end_date or current_date + timedelta(days=365 * 2)  # 2 years ahead
        self.start_days = start_days or 0
        self.end_days = end_days or 0
        self.from_today = from_today or False
        if self.from_today:
            self.start_date = current_date

        self.format = format or "%d/%m/%Y, %H:%M:%S"
        super().__init__(*args, **kwargs)

    def next_value(self) -> datetime:
        """Generate a random datetime between start_date and end_date."""
        start_ts = self.start_date.timestamp()
        end_ts = self.end_date.timestamp()

        # random.uniform returns a float in [start, end)
        rand_ts = self.rand.uniform(start_ts, end_ts)
        return datetime.fromtimestamp(rand_ts)

    def next_value_as_string(self) -> str:
        """Return a formatted random datetime as string."""
        value = self.next_value()
        return value.strftime(self.format)