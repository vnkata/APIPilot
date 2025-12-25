import random
import logging
from datetime import datetime, timedelta
from pydantic import Field
from . import RandomGenerator

logger = logging.getLogger(__name__)


class RandomDateGenerator(RandomGenerator):
    """Random date generator with optional start/end range and formatting."""

    start_date: datetime | None = None
    end_date: datetime | None = None
    start_days: int = 0
    end_days: int = 0
    from_today: bool = False
    format: str = Field(default="yyyy-MM-dd HH:mm:ss")

    def __init__(self, start_date=None, end_date=None,start_days=None,end_days=None, from_today=None, format=None, *args, **kwargs):
        current_date = datetime.now()
        self.start_date = start_date or current_date - timedelta(days=365 * 10)
        self.end_date = end_date
        self.start_days = start_days or 0
        self.end_days = end_days or 0
        self.from_today = from_today or False
        self.format = format or "yyyy-MM-dd HH:mm:ss"
        super().__init__(*args, **kwargs)

    def model_post_init(self, __context):
        super().model_post_init(__context)

        now = datetime.now()

        # Convert Java-style format to Python strftime format
        self.format = (
            self.format.replace("yyyy", "%Y")
            .replace("MM", "%m")
            .replace("dd", "%d")
            .replace("HH", "%H")
            .replace("mm", "%M")
            .replace("ss", "%S")
        )

        # Default date range
        if self.start_date is None:
            self.start_date = now - timedelta(days=365 * 10)  # 10 years ago
        if self.end_date is None:
            self.end_date = now + timedelta(days=365 * 2)  # 2 years ahead

        # Handle from_today flag
        if self.from_today:
            self.start_date = now

        # Apply relative day offsets if specified
        if self.start_days != 0:
            self.start_date = now + timedelta(days=self.start_days)
        if self.end_days != 0:
            self.end_date = now + timedelta(days=self.end_days)

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

    # -------------------
    # Java-style setters
    # -------------------
    def set_start_date(self, start_date_str: str):
        try:
            self.start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Error parsing start date: {start_date_str}", exc_info=e)

    def set_end_date(self, end_date_str: str):
        try:
            self.end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Error parsing end date: {end_date_str}", exc_info=e)

    def set_format(self, fmt: str):
        self.format = fmt

    def set_from_today(self, from_today: bool):
        """If true, start_date is set to today; else 10 years ago."""
        now = datetime.now()
        if from_today:
            self.start_date = now
        else:
            self.start_date = now - timedelta(days=365 * 10)
        self.from_today = from_today

    def set_start_days(self, days: int):
        """Set start_date relative to today."""
        self.start_days = days
        self.start_date = datetime.now() + timedelta(days=days)

    def set_end_days(self, days: int):
        """Set end_date relative to today."""
        self.end_days = days
        self.end_date = datetime.now() + timedelta(days=days)
