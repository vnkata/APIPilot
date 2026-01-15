"""Unit tests for RandomColorGenerator."""
import pytest
import re
from api_testing.inputs.random_color_generator import RandomColorGenerator


class TestRandomColorGenerator:
    """Test suite for RandomColorGenerator."""

    def test_initialization_default_hex(self):
        """Test default initialization is hex format."""
        gen = RandomColorGenerator()
        assert gen.format == "hex"

    def test_initialization_rgb(self):
        """Test initialization with rgb format."""
        gen = RandomColorGenerator(format="rgb")
        assert gen.format == "rgb"

    def test_initialization_hsl(self):
        """Test initialization with hsl format."""
        gen = RandomColorGenerator(format="hsl")
        assert gen.format == "hsl"

    def test_initialization_name(self):
        """Test initialization with name format."""
        gen = RandomColorGenerator(format="name")
        assert gen.format == "name"

    def test_initialization_with_seed(self):
        """Test that seed produces reproducible results."""
        gen1 = RandomColorGenerator(format="hex", seed=12345)
        gen2 = RandomColorGenerator(format="hex", seed=12345)
        
        # HSL format uses internal rand, so should be reproducible
        gen3 = RandomColorGenerator(format="hsl", seed=12345)
        gen4 = RandomColorGenerator(format="hsl", seed=12345)
        
        result1 = gen3.next_value()
        result2 = gen4.next_value()
        assert result1 == result2

    def test_next_value_hex_format(self):
        """Test hex color format is valid."""
        gen = RandomColorGenerator(format="hex", seed=42)
        for _ in range(10):
            value = gen.next_value()
            # Hex color should match #RRGGBB pattern
            assert re.match(r'^#[0-9a-fA-F]{6}$', value), f"Invalid hex color: {value}"

    def test_next_value_rgb_format(self):
        """Test rgb color format is valid."""
        gen = RandomColorGenerator(format="rgb", seed=42)
        for _ in range(10):
            value = gen.next_value()
            # RGB format should be like "R,G,B"
            parts = value.split(',')
            assert len(parts) == 3, f"Invalid RGB format: {value}"
            for part in parts:
                num = int(part.strip())
                assert 0 <= num <= 255, f"RGB value out of range: {num}"

    def test_next_value_hsl_format(self):
        """Test hsl color format is valid."""
        gen = RandomColorGenerator(format="hsl", seed=42)
        for _ in range(10):
            value = gen.next_value()
            # HSL format should be like "hsl(H, S%, L%)"
            assert value.startswith("hsl("), f"Invalid HSL format: {value}"
            assert value.endswith(")"), f"Invalid HSL format: {value}"

    def test_next_value_name_format(self):
        """Test name color format returns a string."""
        gen = RandomColorGenerator(format="name", seed=42)
        for _ in range(10):
            value = gen.next_value()
            assert isinstance(value, str), f"Color name should be a string: {value}"
            assert len(value) > 0, "Color name should not be empty"

    def test_next_value_as_string(self):
        """Test that next_value_as_string returns same as next_value."""
        gen = RandomColorGenerator(format="hex", seed=42)
        # Both methods should return string
        value = gen.next_value_as_string()
        assert isinstance(value, str)

    def test_unsupported_format_raises_error(self):
        """Test that unsupported format raises ValueError."""
        gen = RandomColorGenerator(format="hex")
        gen.format = "invalid_format"
        
        with pytest.raises(ValueError, match="Unsupported color format"):
            gen.next_value()

    def test_case_insensitive_format(self):
        """Test that format is case-insensitive."""
        gen1 = RandomColorGenerator(format="HEX")
        gen2 = RandomColorGenerator(format="RGB")
        gen3 = RandomColorGenerator(format="HSL")
        gen4 = RandomColorGenerator(format="NAME")
        
        assert gen1.format == "hex"
        assert gen2.format == "rgb"
        assert gen3.format == "hsl"
        assert gen4.format == "name"

    def test_description_exists(self):
        """Test that description attribute exists."""
        gen = RandomColorGenerator()
        assert gen.description is not None
        assert len(gen.description) > 0

    def test_multiple_generations_vary(self):
        """Test that multiple generations produce varying results."""
        gen = RandomColorGenerator(format="hex", seed=42)
        results = set()
        for _ in range(50):
            results.add(gen.next_value())
        
        # Should have generated at least several unique colors
        assert len(results) > 10
