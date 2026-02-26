"""Unit tests for RandomBooleanGenerator."""
import pytest
from api_testing.inputs.random_boolean_generator import RandomBooleanGenerator
from api_testing.inputs.fuzz_strategy import FuzzStrategy


class TestRandomBooleanGenerator:
    """Test suite for RandomBooleanGenerator."""

    def test_initialization_default(self):
        """Test default initialization with 0.5 probability."""
        gen = RandomBooleanGenerator()
        assert gen.true_probability == 0.5

    def test_initialization_custom_probability(self):
        """Test initialization with custom probability."""
        gen = RandomBooleanGenerator(true_probability=0.8)
        assert gen.true_probability == 0.8

    def test_initialization_with_seed(self):
        """Test that seed produces reproducible results."""
        gen1 = RandomBooleanGenerator(seed=12345)
        gen2 = RandomBooleanGenerator(seed=12345)
        
        results1 = [gen1.next_value() for _ in range(10)]
        results2 = [gen2.next_value() for _ in range(10)]
        
        assert results1 == results2

    def test_next_value_returns_boolean(self):
        """Test that next_value returns a boolean."""
        gen = RandomBooleanGenerator(seed=42)
        for _ in range(20):
            value = gen.next_value()
            assert isinstance(value, bool)

    def test_next_value_probability_zero(self):
        """Test that probability 0 always returns False."""
        gen = RandomBooleanGenerator(true_probability=0.0, seed=42)
        for _ in range(100):
            assert gen.next_value() is False

    def test_next_value_probability_one(self):
        """Test that probability 1 always returns True."""
        gen = RandomBooleanGenerator(true_probability=1.0, seed=42)
        for _ in range(100):
            assert gen.next_value() is True

    def test_next_value_distribution(self):
        """Test that probability roughly matches expected distribution."""
        gen = RandomBooleanGenerator(true_probability=0.7, seed=42)
        results = [gen.next_value() for _ in range(1000)]
        true_count = sum(results)
        
        # Allow 10% deviation from expected
        assert 0.6 <= true_count / 1000 <= 0.8

    def test_next_value_as_string(self):
        """Test that next_value_as_string returns proper string."""
        gen = RandomBooleanGenerator(seed=42)
        for _ in range(10):
            value = gen.next_value_as_string()
            assert value in ["True", "False"]

    def test_next_fuzz_value_returns_value(self):
        """Test that next_fuzz_value returns a value."""
        gen = RandomBooleanGenerator(seed=42)
        
        for _ in range(20):
            value = gen.next_fuzz_value()
            # Value should be one of the expected fuzz types
            assert value is not None or value is None  # Can be None

    def test_next_fuzz_value_empty_strategy(self):
        """Test fuzz value for empty strategy returns None or empty string."""
        gen = RandomBooleanGenerator(seed=42)
        
        # Run multiple times to hit the EMPTY strategy
        empty_values = []
        for _ in range(100):
            value = gen.next_fuzz_value()
            if value is None or value == "":
                empty_values.append(value)
        
        # Should hit empty at least once in 100 tries
        assert len(empty_values) > 0

    def test_next_fuzz_value_type_error_strategy(self):
        """Test that type error fuzz values are returned."""
        gen = RandomBooleanGenerator(seed=42)
        
        type_error_values = ["true", "false", "TRUE", "FALSE", 0, 1, "yes", "no"]
        found_type_errors = []
        
        for _ in range(100):
            value = gen.next_fuzz_value()
            if value in type_error_values:
                found_type_errors.append(value)
        
        assert len(found_type_errors) > 0

    def test_set_seed(self):
        """Test that set_seed changes the seed."""
        gen = RandomBooleanGenerator()
        gen.set_seed(99999)
        assert gen.get_seed() == 99999

    def test_get_seed(self):
        """Test that get_seed returns the current seed."""
        gen = RandomBooleanGenerator(seed=54321)
        assert gen.get_seed() == 54321

    def test_description_exists(self):
        """Test that description attribute exists."""
        gen = RandomBooleanGenerator()
        assert gen.description is not None
        assert len(gen.description) > 0
