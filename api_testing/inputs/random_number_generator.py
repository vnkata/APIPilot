import random
from enum import Enum
from pydantic import Field
from typing import Any
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

    def __init__(self, type: DataType = None, min=None, max=None, *args, **kwargs):
        self.type = type
        self.min = min
        self.max = max
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
        super().__init__(*args, **kwargs)

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
