from abc import ABC, abstractmethod
import random
import string
from typing import Any

from api_testing.inputs.fuzz_strategy import FuzzStrategy

class RandomGenerator(ABC):
    description: str = ""

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
        pass


    def _get_boundary_cluster(self) -> str:
        """Generates dynamic memory and size limit stress tests."""
        factories = [
            lambda: "",  # Empty string
            lambda: "A" * self.rand.randint(1024, 1024 * 1024), # Large strings (1KB to 1MB)
            lambda: str(self.rand.getrandbits(self.rand.randint(128, 512))),  # Massive numbers
            lambda: "0" * self.rand.randint(10, 100) + "1"  # Long leading zeros
        ]
        return self.rand.choice(factories)()

    def _get_injection_cluster(self) -> str:
        """Generates dynamic injection payloads (SSTI, SQLi, Command)."""
        # Dynamic command injection
        commands = ["id", "whoami", "ls -la", "sleep 5", "env"]
        # Dynamic SQLi patterns
        sqli_templates = ["' OR '{0}'='{0}", "') OR ('{0}'='{0}", "'; WAITFOR DELAY '0:0:{1}'--"]
        
        factories = [
            lambda: f"{{{{{self.rand.randint(1, 999)}*{self.rand.randint(1, 999)}}}}}", # Dynamic SSTI
            lambda: self.rand.choice(sqli_templates).format(self.rand.randint(1, 9), self.rand.randint(2, 5)),
            lambda: f"; {self.rand.choice(commands)} #", # Dynamic Command Injection
            lambda: f'{{ "$gt": "{self.rand.choice(["", "0", "a"])}" }}' # NoSQL
        ]
        return self.rand.choice(factories)()

    def _get_encoding_cluster(self) -> str:
        """Generates advanced Unicode chaos, bypasses, and obfuscation."""
        
        def unicode_homograph() -> str:
            """Characters that look like ASCII but are different Unicode (Homograph Attack)."""
            # Example: 'a' vs Cyrillic 'а', 'o' vs Greek 'ο'
            homoglyphs = {'a': 'а', 'e': 'е', 'i': 'і', 'o': 'ο', 'p': 'р'}
            base = "".join(self.rand.choices(string.ascii_letters, k=10))
            # Randomly replace some characters with their homoglyphs
            return "".join(homoglyphs.get(c, c) if self.rand.random() > 0.5 else c for c in base)

        def directional_overrides() -> str:
            """Using Right-to-Left Override (RLO) to flip text (e.g., for file extension spoofing)."""
            rlo = "\u202e"
            lro = "\u202d"
            # Spreads dangerous extensions: exe.txt -> txt.exe
            text = "exe.txt"
            return f"{rlo}{text[::-1]}{lro}"

        def overlong_utf8() -> str:
            """Simulate overlong UTF-8 sequences that can bypass basic filters."""
            # Common bypasses for dots or slashes using non-standard encodings
            overlong_patterns = [
                "%c0%af",         # Overlong '/'
                "%c0%ae%c0%ae",   # Overlong '..'
                "\xe0\x80\xaf",   # 3-byte overlong '/'
                "\xf0\x80\x80\xaf" # 4-byte overlong '/'
            ]
            return self.rand.choice(overlong_patterns) + "".join(self.rand.choices(string.ascii_letters, k=5))

        def multi_byte_chaos() -> str:
            """Surrogates, Private Use Areas, and Unassigned code points."""
            factories = [
                lambda: "".join(chr(self.rand.randint(0xD800, 0xDFFF)) for _ in range(3)), # Broken Surrogates
                lambda: "".join(chr(self.rand.randint(0xE000, 0xF8FF)) for _ in range(5)), # Private Use Area
                lambda: "".join(chr(self.rand.randint(0x10000, 0x10FFFF)) for _ in range(2)), # Supplementary planes (Emoji/Ancient)
                lambda: "A" + "\u034F" * 5 + "B" # Combining Grapheme Joiner chaos
            ]
            return self.rand.choice(factories)()

        def obfuscated_bypasses() -> str:
            """Double, Triple, and Half-encoding tricks."""
            target = self.rand.choice(["<script>", "../../etc/passwd", "admin"])
            factories = [
                lambda: target.replace("/", "%252f"), # Double URL encoding
                lambda: "".join(f"&#x{ord(c):02x};" for c in target), # Hex NCRs
                lambda: "".join(f"\\u{ord(c):04x}" for c in target), # Unicode Escape
                lambda: "%u00" + "%u00".join(f"{ord(c):02x}" for c in target) # IIS-style Unicode encoding
            ]
            return self.rand.choice(factories)()

        # Select one of the complex sub-clusters
        sub_clusters = [
            unicode_homograph,
            directional_overrides,
            overlong_utf8,
            multi_byte_chaos,
            obfuscated_bypasses,
            lambda: "\0" * self.rand.randint(1, 10) # Dynamic Null byte padding
        ]
        
        return self.rand.choice(sub_clusters)()

    def _get_structural_cluster(self) -> str:
        """Generates broken or deeply nested structures."""
        depth = self.rand.randint(100, 1000)
        factories = [
            lambda: "[" * depth + "]" * depth,
            lambda: '{"a":' * depth + "1" + "}" * depth,
            lambda: self.rand.choice(["null", "undefined", "true", "false", "NaN", "Infinity", "-0"]),
            lambda: "{" + "".join(self.rand.choices(string.ascii_letters, k=1000)) + "}" # Unclosed/Large keys
        ]
        return self.rand.choice(factories)()

    # --- Main Fuzzing Entry Point ---

    def next_fuzz_value(self, strategy: FuzzStrategy, context_pool=None, *args, **kargs) -> Any:
        """Selects a cluster and generates a dynamic value."""
        
        clusters = {
            "BOUNDARY": self._get_boundary_cluster,
            "INJECTION": self._get_injection_cluster,
            "ENCODING": self._get_encoding_cluster,
            "STRUCTURE": self._get_structural_cluster
        }
        
        strategy = self.rand.choice(list(clusters.keys()))
        return clusters[strategy]()