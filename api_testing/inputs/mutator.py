import random
import string
from typing import Any, List, Union
from datetime import datetime, timedelta

class Mutator:
    """
    Logic to mutate valid values into invalid or boundary values for fuzzing.
    """

    def __init__(self, rand_inst: random.Random = None):
        # Use provided random instance for reproducibility or create a new one
        self.rand = rand_inst or random.Random()
        
        # Common fuzzing payloads
        self.injection_strings = [
            "' OR '1'='1",
            "<script>alert(1)</script>",
            "../../etc/passwd",
            "%s%p%x%d",
            "\\x00\\xFF",
            "{}",
            "[]",
            "null"
        ]

    def mutate(self, value: Any) -> Any:
        """
        Entry point to mutate a value based on its detected type.
        """
        if isinstance(value, str):
            return self.mutate_string(value)
        elif isinstance(value, (int, float)):
            return self.mutate_number(value)
        elif isinstance(value, bool):
            return self.mutate_boolean(value)
        elif isinstance(value, (datetime, str)) and self._is_date(value):
            return self.mutate_date(value)
        elif isinstance(value, (bytes, bytearray)):
            return self.mutate_bytes(value)
        
        # If type is unknown, return None or a random object to break the API
        return self.rand.choice([None, {}, []])

    def mutate_string(self, value: str) -> str:
        """Destroys a string using various fuzzing strategies."""
        strategy = self.rand.choice(["empty", "overflow", "injection", "null_byte", "format_string"])
        
        if strategy == "empty":
            return ""
        if strategy == "overflow":
            return "A" * 10000
        if strategy == "injection":
            return self.rand.choice(self.injection_strings)
        if strategy == "null_byte":
            return value + "\0"
        if strategy == "format_string":
            return "%n%s%p" * 10
        return value

    def mutate_number(self, value: Union[int, float]) -> Any:
        """Destroys a numeric value."""
        strategy = self.rand.choice(["zero", "overflow", "sign_flip", "type_change", "nan","injection"])
        
        if strategy == "zero":
            return 0
        if strategy == "overflow":
            return 10**308 if isinstance(value, float) else 2**128
        if strategy == "sign_flip":
            return value * -1 if value != 0 else -1
        if strategy == "type_change":
            return str(value) # Change 123 to "123"
        if strategy == "nan" and isinstance(value, float):
            return float('nan')
        if strategy == "injection":
            return self.rand.choice(self.injection_strings)
        return value

    def mutate_boolean(self, value: bool) -> Any:
        """Destroys a boolean value."""
        # APIs often crash when receiving "true" instead of true or a number/null
        return self.rand.choice([not value, "True", "False", 0, 1, None])

    def mutate_date(self, value: Any) -> str:
        """Destroys date logic."""
        strategy = self.rand.choice(["invalid_day", "far_past", "far_future", "wrong_format"])
        
        if strategy == "invalid_day":
            return "2025-02-31" # Date that never exists
        if strategy == "far_past":
            return "0001-01-01"
        if strategy == "far_future":
            return "9999-12-31"
        if strategy == "wrong_format":
            return datetime.now().strftime("%d/%m/%Y %H:%M:%S") # Often APIs expect ISO8601
        return str(value)

    def mutate_bytes(self, value: bytes) -> bytes:
        """Destroys file content or byte streams."""
        if not value:
            return b"\xFF\xFE\xFD"
            
        strategy = self.rand.choice(["empty", "truncate", "bit_flip", "corrupt_header"])
        
        if strategy == "empty":
            return b""
        if strategy == "truncate":
            return value[:len(value)//2]
        if strategy == "bit_flip":
            # Flip a random bit in a random byte
            mutable = bytearray(value)
            idx = self.rand.randint(0, len(mutable) - 1)
            mutable[idx] = mutable[idx] ^ 0xFF
            return bytes(mutable)
        if strategy == "corrupt_header":
            # Replace the first 4 bytes (magic numbers) with random noise
            return self.rand.randbytes(4) + value[4:]
        return value

    def _is_date(self, value: Any) -> bool:
        """Helper to detect if a string might be a date."""
        if isinstance(value, datetime):
            return True
        # Simple check for date separators
        return isinstance(value, str) and any(sep in value for sep in ["-", "/", ":"])