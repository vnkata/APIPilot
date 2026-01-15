
from abc import ABC, abstractmethod
import random

from api_testing.inputs.fuzz_strategy import FuzzStrategy


class RandomGenerator(ABC):
    description: str = ""
    """Superclass for random generators with seed management."""

    def __init__(self, seed: int | None = None):
        self.rand = random.Random()
        self.seed = seed if seed is not None else random.getrandbits(64)
        self.rand.seed(self.seed)

    def set_seed(self, seed: int):
        self.seed = seed
        self.rand.seed(seed)

    def get_seed(self) -> int:
        return self.seed

    @abstractmethod
    def next_value(self):
        """Generate the next random value."""
        pass
    def next_fuzz_value(self) -> str:
        """Generate a random fuzzy value by randomly selecting a strategy."""
        
        # Randomly pick a strategy
        strategy = self.rand.choice(["BOUNDARY", "INJECTION", "ENCODING", "STRUCTURE"])
        
        # 1. Extreme Boundaries
        if strategy == "BOUNDARY":
            return self.rand.choice([
                "",                          # Empty
                "A" * 1024 * 1024,           # 1MB string (Memory pressure)
                "9" * 50,                    # Massive integer as string
            ])

        # 2. Advanced Injections
        if strategy == "INJECTION":
            return self.rand.choice([
                # SSTI (Server Side Template Injection)
                "{{7*7}}", 
                "${7*7}",
                # NoSQL Injection
                '{"$gt": ""}',
                # Blind SQLi / Time-based
                "'; WAITFOR DELAY '0:0:5'--",
                "'); SELECT pg_sleep(5);--",
                # Command Injection
                "; /usr/bin/id",
                "& whoami &",
            ])

        # 3. Encoding & Unicode Chaos
        if strategy == "ENCODING":
            return self.rand.choice([
                "\0",                        # Null byte
                "\ufeff",                    # Byte Order Mark (BOM)
                "జ్ఞా",                      # Complex script (Power symbol bug)
                "A\u030a\u030a\u030a",       # Combining characters
                "%252f..%252fetc%252fpasswd", # Double URL encoding
                "String.fromCharCode(0)",    # JS Eval bypass
            ])

        # 4. Structural/Logic
        if strategy == "STRUCTURE":
            return self.rand.choice([
                "[" * 500 + "]" * 500,       # Deeply nested JSON
                '{"a":' * 500 + "1" + "}" * 500,
                "null",
                "undefined",
                "true",
                "false",
            ])

        return ""