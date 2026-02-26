import random
import logging
from datetime import datetime, timedelta
from typing import Any
from pydantic import Field

from api_testing.inputs.fuzz_strategy import FuzzStrategy
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
        from_today (bool): If True, generate dates relative to the current day.
        format (str): The output date format string (default: "yyyy-MM-dd HH:mm:ss")
    """
    def __init__(self, start_date=None, end_date=None, from_today=None, format=None, *args, **kwargs):
        current_date = datetime.now()
        self.start_date = start_date or current_date - timedelta(days=365 * 10) # 10 years
        self.end_date = end_date or current_date + timedelta(days=365 * 2)  # 2 years ahead
        self.from_today = from_today or False
        if self.from_today:
            self.start_date = current_date

        self.format = format or "%d/%m/%Y, %H:%M:%S"
        super().__init__(*args, **kwargs)

    def next_value(self ,*args, **kargs) -> datetime:
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
    def next_fuzz_value(self) -> Any:
        """Randomly selects a date-specific fuzzing strategy and returns a value."""
        
        # Define only the strategies implemented within this specific logic
        supported_strategies = [
            FuzzStrategy.EMPTY,
            FuzzStrategy.LOGIC_ERROR,
            FuzzStrategy.FORMAT_ERROR
        ]
        
        # Internal random selection
        strategy = self.rand.choice(supported_strategies)

        if strategy == FuzzStrategy.EMPTY:
            return self.rand.choice([None, ""])

        if strategy == FuzzStrategy.LOGIC_ERROR:
            year = self.rand.randint(1900, 2100)
            logic_clusters = [
                f"{year}-02-{self.rand.randint(30, 31)}", # February 30th/31st
                f"{year}-{self.rand.randint(13, 99)}-01", # Month out of range
                f"{year}-01-{self.rand.randint(32, 99)}", # Day out of range
                f"0000-{self.rand.randint(0, 99):02}-{self.rand.randint(0, 99):02}", # Year zero/invalid
            ]
            return self.rand.choice(logic_clusters)

        # Mismatched standards and data types
        if strategy == FuzzStrategy.FORMAT_ERROR:
            val = self.next_value()
            wrong_formats = [
                str(val.timestamp()),
                val.isoformat(),
                val.strftime("%Y/%m/%d"),
                val.strftime("%A, %d %B %Y"), # Full text format
                "not-a-date-string",
                self.rand.randint(-1000000, 1000000) # Raw integer as date
            ]
            return self.rand.choice(wrong_formats)

        return None
    
    
