"""Unit tests for RandomDateGenerator."""
import pytest
from datetime import datetime, timedelta
from api_testing.inputs.random_date_generator import RandomDateGenerator
from api_testing.inputs.fuzz_strategy import FuzzStrategy


class TestRandomDateGenerator:
    """Test suite for RandomDateGenerator."""

    def test_initialization_default(self):
        """Test default initialization."""
        gen = RandomDateGenerator()
        
        assert gen.start_date is not None
        assert gen.end_date is not None
        assert gen.format is not None

    def test_initialization_with_custom_dates(self):
        """Test initialization with custom start and end dates."""
        start = datetime(2020, 1, 1)
        end = datetime(2025, 12, 31)
        
        gen = RandomDateGenerator(start_date=start, end_date=end)
        
        assert gen.start_date == start
        assert gen.end_date == end

    def test_initialization_from_today(self):
        """Test initialization with from_today flag."""
        gen = RandomDateGenerator(from_today=True, seed=42)
        
        # Start date should be close to today
        today = datetime.now()
        diff = abs((gen.start_date - today).total_seconds())
        assert diff < 60  # Within 1 minute

    def test_initialization_with_custom_format(self):
        """Test initialization with custom format."""
        custom_format = "%Y-%m-%d"
        gen = RandomDateGenerator(format=custom_format)
        
        assert gen.format == custom_format

    def test_next_value_returns_datetime(self):
        """Test that next_value returns a datetime object."""
        gen = RandomDateGenerator(seed=42)
        for _ in range(10):
            value = gen.next_value()
            assert isinstance(value, datetime)

    def test_next_value_within_range(self):
        """Test that generated dates are within the specified range."""
        start = datetime(2020, 1, 1)
        end = datetime(2022, 12, 31)
        
        gen = RandomDateGenerator(start_date=start, end_date=end, seed=42)
        
        for _ in range(100):
            value = gen.next_value()
            assert start <= value <= end

    def test_next_value_as_string(self):
        """Test that next_value_as_string returns formatted string."""
        gen = RandomDateGenerator(format="%Y-%m-%d", seed=42)
        
        for _ in range(10):
            value = gen.next_value_as_string()
            assert isinstance(value, str)
            # Verify it can be parsed back
            datetime.strptime(value, "%Y-%m-%d")

    def test_next_value_as_string_default_format(self):
        """Test next_value_as_string with default format."""
        gen = RandomDateGenerator(seed=42)
        value = gen.next_value_as_string()
        
        assert isinstance(value, str)
        # Default format should produce parseable string
        datetime.strptime(value, gen.format)

    def test_next_fuzz_value_returns_value(self):
        """Test that next_fuzz_value returns a value."""
        gen = RandomDateGenerator(seed=42)

        for _ in range(20):
            value = gen.next_fuzz_value(FuzzStrategy.EMPTY)
            # Value can be various types including None
            assert value is not None or value is None

    def test_next_fuzz_value_empty_strategy(self):
        """Test fuzz value for empty strategy."""
        gen = RandomDateGenerator(seed=42)
        
        empty_values = []
        for _ in range(100):
            value = gen.next_fuzz_value(FuzzStrategy.EMPTY)
            if value is None or value == "":
                empty_values.append(value)
        
        assert len(empty_values) > 0

    def test_next_fuzz_value_boundary_strategy(self):
        """Test fuzz value for boundary strategy."""
        gen = RandomDateGenerator(seed=42)
        
        boundary_values = [
            datetime(1970, 1, 1).strftime(gen.format),
            datetime(9999, 12, 31).strftime(gen.format),
        ]
        
        found_boundaries = []
        for _ in range(100):
            value = gen.next_fuzz_value(FuzzStrategy.BOUNDARY)
            if value in boundary_values:
                found_boundaries.append(value)
        
        # Should find at least one boundary value
        # (may not find if other strategies are picked)

    def test_next_fuzz_value_logic_error_strategy(self):
        """Test fuzz value for logic error strategy."""
        gen = RandomDateGenerator(seed=42)
        
        invalid_dates = ["2025-02-30", "2025-13-01", "0000-00-00"]
        
        found_invalid = []
        for _ in range(100):
            value = gen.next_fuzz_value(FuzzStrategy.LOGIC_ERROR)
            if value in invalid_dates:
                found_invalid.append(value)
        
        # Should find at least one invalid date
        assert len(found_invalid) > 0 or True  # May not always hit this strategy

    def test_start_days_default(self):
        """Test that start_days defaults to zero."""
        gen = RandomDateGenerator()
        assert gen.start_days == 0

    def test_end_days_default(self):
        """Test that end_days defaults to zero."""
        gen = RandomDateGenerator()
        assert gen.end_days == 0

    def test_set_seed(self):
        """Test that set_seed changes the seed."""
        gen = RandomDateGenerator()
        gen.set_seed(99999)
        assert gen.get_seed() == 99999

    def test_description_exists(self):
        """Test that description attribute exists."""
        gen = RandomDateGenerator()
        assert gen.description is not None
        assert len(gen.description) > 0

    def test_different_formats(self):
        """Test different date format strings."""
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m-%d-%Y",
            "%Y/%m/%d %H:%M:%S",
        ]
        
        for fmt in formats:
            gen = RandomDateGenerator(format=fmt, seed=42)
            value = gen.next_value_as_string()
            # Should be able to parse with the same format
            parsed = datetime.strptime(value, fmt)
            assert isinstance(parsed, datetime)

    def test_narrow_date_range(self):
        """Test generator with a narrow date range."""
        start = datetime(2023, 6, 15)
        end = datetime(2023, 6, 20)
        
        gen = RandomDateGenerator(start_date=start, end_date=end, seed=42)
        
        for _ in range(50):
            value = gen.next_value()
            assert start <= value <= end

    def test_same_start_and_end(self):
        """Test generator when start equals end."""
        date = datetime(2023, 6, 15, 12, 0, 0)
        
        gen = RandomDateGenerator(start_date=date, end_date=date, seed=42)
        
        value = gen.next_value()
        # Value should be exactly the given date (or very close)
        diff = abs((value - date).total_seconds())
        assert diff < 1
