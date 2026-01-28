import random
from enum import Enum
from pydantic import Field
from typing import Any, Set

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator


class DataType(str, Enum):
    INTEGER = "INTEGER"
    INT32 = "INT32"
    INT64 = "INT64"
    DOUBLE = "DOUBLE"
    FLOAT = "FLOAT"
    LONG = "LONG"
    NUMBER = "NUMBER"

    def is_number(self) -> bool:
        return self in {
            DataType.INTEGER,
            DataType.INT32,
            DataType.INT64,
            DataType.DOUBLE,
            DataType.FLOAT,
            DataType.LONG,
            DataType.NUMBER,
        }


class RandomNumberGenerator(RandomGenerator):
    """Random number generator with optional min/max range by DataType."""

    type: DataType
    min: Any = Field(default=None)
    max: Any = Field(default=None)
    description: str = """A generator that produces random numeric values within a specified range.
    Attributes:
        type (DataType): Defines the numeric type to generate 
            (e.g., INTEGER, FLOAT, DOUBLE, LONG).
        min (Any): The minimum possible value for the generated number (optional).
        max (Any): The maximum possible value for the generated number (optional).
    """
    supported_strategies: Set[FuzzStrategy] = {"boundary", "type_error", "overflow"}

    def model_post_init(self, __context):
        super().model_post_init(__context)

        if not self.type.is_number():
            raise ValueError("The requested type is not a number")

        # Initialize default min/max values based on type
        if self.type in {DataType.INTEGER, DataType.INT32, DataType.INT64}:
            self.min = self.min if self.min is not None else -2**31
            self.max = self.max if self.max is not None else 2**31 - 1
        elif self.type in {DataType.DOUBLE, DataType.NUMBER}:
            self.min = self.min if self.min is not None else -1e308
            self.max = self.max if self.max is not None else 1e308
        elif self.type == DataType.FLOAT:
            self.min = self.min if self.min is not None else -3.4e38
            self.max = self.max if self.max is not None else 3.4e38
        elif self.type == DataType.LONG:
            self.min = self.min if self.min is not None else -2**63
            self.max = self.max if self.max is not None else 2**63 - 1

    def next_value(self) -> Any:
        """Generate a random numeric value according to the DataType."""
        if self.type in {DataType.INTEGER, DataType.INT32, DataType.INT64, DataType.LONG}:
            return self.rand.randint(int(self.min), int(self.max))
        elif self.type in {DataType.DOUBLE, DataType.NUMBER}:
            return self.rand.uniform(float(self.min), float(self.max))
        elif self.type == DataType.FLOAT:
            random_float = self.rand.random()
            return float(self.min) + random_float * (float(self.max) - float(self.min))
        else:
            raise ValueError(f"Unsupported data type for random generation: {self.type}")

    def next_value_as_string(self) -> str:
        """Generate next random value as string."""
        return str(self.next_value())
    def next_fuzz_value(self, strategy: FuzzStrategy) -> Any:
        """
        Numeric-specific fuzzing strategies focusing on alternate bases, 
        encoding artifacts, and boundary conditions.
        """
        # Generate a valid number within the set range to use as a base for mutations
        base_val = self.next_value()
        base_int = int(base_val) if self.type.is_number() else 0

        if strategy == FuzzStrategy.ENCODING:
            return self.rand.choice([
                # 1. Hexadecimal Representations
                hex(base_int),                      # Standard: 0x1a
                hex(base_int).upper().replace("X", "x"), # Uppercase: 0x1A
                f"%{base_int % 255:02x}",           # URL-encoded hex byte: %1a
                
                # 2. Null-Byte Injection (Testing for string termination vulnerabilities)
                f"{base_int}%00",                   # URL-encoded null
                f"{base_int}\0",                    # Literal null byte
                
                # 3. Whitespace & Padding (Testing parser trimming logic)
                f" {base_int} ",                    # Leading/Trailing space
                f"{base_int}%20",                   # URL-encoded space
                f"\t{base_int}\n",                  # Tabs and Newlines
                f"{base_int:010d}",                 # Excessive leading zeros (e.g., 0000000123)
                
                # 4. Alternative Number Bases
                bin(base_int),                      # Binary: 0b1101
                oct(base_int)                       # Octal: 0o17
            ])

        if strategy == FuzzStrategy.BOUNDARY:
            # Focus on integer limits and signs
            try:
                min_underflow = int(self.min) - 1   # Underflow (integer)
            except (ValueError, OverflowError, TypeError):
                # Fallback: if we cannot safely convert to int, just reuse the minimum
                min_underflow = self.min

            try:
                max_overflow = int(self.max) + 1    # Overflow (integer)
            except (ValueError, OverflowError, TypeError):
                # Fallback: if we cannot safely convert to int, just reuse the maximum
                max_overflow = self.max

            return self.rand.choice([
                self.min,                           # Absolute minimum
                self.max,                           # Absolute maximum
                min_underflow,                      # Underflow
                max_overflow,                       # Overflow
                0,                                  # Zero
                -1,                                 # Negative boundary
                0.00000000001                       # Extremely small positive float
            ])

        if strategy == FuzzStrategy.FORMAT_ERROR:
            return self.rand.choice([
                f"{base_int}.{base_int}.{base_int}",# Multiple decimal points
                f"{base_int},000",                  # Thousands separator (often breaks parsers)
                f"+{base_int}",                     # Explicit positive sign
                "NaN",                              # Not a Number
                "Infinity",                         # Mathematical infinity
                "-Infinity"
            ])

        if strategy == FuzzStrategy.TYPE_ERROR:
            return self.rand.choice([
                str(base_int),                      # Number as a string (if the API expects raw int)
                float(base_int),                    # Float instead of Integer
                [base_int],                         # Number inside a list
                {"value": base_int}                 # Number inside an object
            ])
            
        return base_val