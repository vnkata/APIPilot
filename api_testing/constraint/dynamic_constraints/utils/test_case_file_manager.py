"""Test case file management utilities for Beet."""

import glob
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from api_testing.constraint.dynamic_constraints.test_case import TestCase
from api_testing.utils import to_dict_helper
from api_testing.utils.http import isSuccessful


class TestCaseFileManager:
    """Manages parsing of test case CSV files."""

    def __init__(self, cache_dir: Optional[str] = None) -> None:
        self.cache_dir = cache_dir
        self.testcases = []

    def parse_test_cases_from_history(self):
        files = glob.glob(f"{self.cache_dir}/history/*.har", recursive=True)
        testcases = []
        for file in files:
            testcases.extend(self._process_har_file(file))
        self.testcases = testcases
        return testcases

    def _process_har_file(self, har_path: str) -> List[Dict]:
        """Parse a HAR file, normalize testcases to JSON, and deduplicate."""
        
        def _normalize_testcase(tc: Dict) -> str:
            """Create a stable hash key from testcase JSON."""
            # sort keys to ensure deterministic representation
            normalized = json.dumps(tc, sort_keys=True, separators=(",", ":"))
            return sha256(normalized.encode("utf-8")).hexdigest()

        unique_map: Dict[str, Dict] = {}

        with open(har_path, "r", encoding="utf-8") as f:
            har_data = json.load(f)

        for entry in har_data.get("log", {}).get("entries", []):
            request = entry.get("request", {})
            response = entry.get("response", {})

            if not isSuccessful(response.get("status")):
                continue

            method = (request.get("method") or "").lower()
            path = request.get("path_template")

            parameters = {
                param["name"]: param.get("value")
                for param in request.get("queryString", [])
            }
            parameters.update(request.get("path_params", {}))

            test_case = {
                "test_case_id": entry.get("_id") or f"{method}-{path}",
                "operation_id": f"{method}-{path}",
                "path": path,
                "http_method": method,
                "parameters": parameters,
                "request_body": request.get("postData", {}).get("text"),
                "status_code": response.get("status"),
                "response_body": response.get("content", {}).get("text"),
            }

            key = _normalize_testcase(test_case)

            # deduplicate
            if key not in unique_map:
                unique_map[key] = TestCase(**test_case)

        return list(unique_map.values())

    def save_test_cases(self) -> None:
        file_path = os.path.join(self.cache_dir, "test_cases.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([to_dict_helper(tc) for tc in self.testcases], f)

    def load_test_cases(self, file_path: str | os.PathLike[str] | None = None) -> List[TestCase]:
        resolved_path = Path(file_path) if file_path is not None else Path(self.cache_dir) / "test_cases.json"
        if not resolved_path.exists():
            raise FileNotFoundError(f"Test cases file not found: {resolved_path}")

        with resolved_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)

        self.testcases = [
            TestCase(
                test_case_id=item.get("test_case_id", ""),
                operation_id=item.get("operation_id", ""),
                path=item.get("path", ""),
                http_method=item.get("http_method", ""),
                parameters=item.get("parameters") or {},
                request_body=item.get("request_body"),
                status_code=item.get("status_code"),
                response_body=item.get("response_body"),
            )
            for item in payload
        ]
        return self.testcases
