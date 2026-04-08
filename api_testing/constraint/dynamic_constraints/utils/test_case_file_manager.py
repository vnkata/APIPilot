"""Test case file management utilities for Beet."""

from dataclasses import asdict
import glob
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from api_testing.constraint.dynamic_constraints.test_case import TestCase
from api_testing.utils import to_dict_helper
from api_testing.utils.http import isSuccessful
from . import csv_manager


class TestCaseFileManager:
    """Manages parsing of test case CSV files."""
    def __init__(
        self,
        cache_dir: Optional[str] = None
    ) -> None:
        self.cache_dir = cache_dir
        self.testcases = []
    
    def parse_test_cases_from_history(self):
        files = glob.glob(f'{self.cache_dir}/history/*.har', recursive=True)
        testcases = []
        for file in files:
            testcases.extend(self._process_har_file(file))
        self.testcases = testcases 
        return testcases

    def _process_har_file(self, har_path: str) -> List[Dict[str, str]]:
        """Parse a HAR file and extract test cases."""
        test_cases = []
        with open(har_path, "r", encoding="utf-8") as f:
            har_data = json.load(f)
            entries = har_data["log"]["entries"]
            for i, entry in enumerate(entries, start=1):
                request = entry.get("request", {})
                response = entry.get("response", {})
                if isSuccessful(response.get("status")):
                    test_case = TestCase(
                        test_case_id=f"{entry.get('_id', f'{request.get('method').lower()}-{request.get('path_template')}')}",
                        operation_id=f"{request.get('method').lower()}-{request.get('path_template')}",
                        path=request.get("path_template"),
                        http_method=request.get("method"),
                        parameters={param["name"]: param.get("value") for param in request.get("queryString", [])} | request.get("path_params", {}),
                        request_body=request.get("postData", {}).get("text"),
                        status_code=response.get("status"),
                        response_body=response.get("content", {}).get("text"),
                    )
                    test_cases.append(test_case)
                    # Here you would typically save the test case to a file or database
                    print(f"Extracted test case from entry {i}: {test_case}")
        return test_cases
    
    def save_test_cases(self) -> None:
        file_path = os.path.join(self.cache_dir, "test_cases.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([to_dict_helper(tc) for tc in self.testcases], f)