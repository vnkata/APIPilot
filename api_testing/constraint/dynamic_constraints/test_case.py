"""Test case model for Beet."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")
FLOAT_PATTERN = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+)(?:[eE][+-]?\d+)?$")


def _unwrap_single_value_container(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]

    if isinstance(value, dict) and len(value) == 1:
        key, nested_value = next(iter(value.items()))
        if str(key).lower() in {"val", "value"}:
            return nested_value

    return value


def cast_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    normalized_value = value.strip()
    lowered_value = normalized_value.lower()

    if lowered_value in {"true", "false", "yes", "no", "on", "off"}:
        return lowered_value in {"true", "yes", "on"}

    if INTEGER_PATTERN.fullmatch(normalized_value):
        return int(normalized_value)

    if FLOAT_PATTERN.fullmatch(normalized_value):
        return float(normalized_value)

    if normalized_value.startswith(("[", "{")) and normalized_value.endswith(("]", "}")):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed_value = parser(normalized_value)
                normalized_parsed_value = _unwrap_single_value_container(parsed_value)
                return cast_value(normalized_parsed_value)
            except (ValueError, SyntaxError, json.JSONDecodeError, TypeError):
                continue

    return value

@dataclass
class TestCase:
    """Represents a test case from API calls."""
    
    def __init__(
        self,
        test_case_id: str,
        operation_id: str,
        path: str,
        http_method: str,
        parameters: Optional[Dict[str, str]] = None,
        request_body: Optional[str] = None,
        status_code: Optional[str] = None,
        response_body: Optional[str] = None
    ):
        """Initialize a TestCase.
        
        Args:
            test_case_id: ID of the test case
            operation_id: ID of the operation
            path: API path
            http_method: HTTP method
            parameters: Header parameters
            request_body: Request body
            status_code: Response status code
            response_body: Response body
        """
        self.test_case_id = test_case_id
        self.operation_id = operation_id
        self.path = path
        self.http_method = http_method
        self.parameters =  {k: cast_value(v) for k, v in parameters.items()}
        self.request_body = request_body or {}
        self.status_code = status_code
        self.response_body = response_body
        
    def get_test_case_id(self) -> str:
        """Get the test case ID."""
        return self.test_case_id
    
    def to_dict(self) -> Dict[str, any]:
        """Convert TestCase to a dictionary with parsed response_body.
        
        Returns:
            Dictionary representation of the test case with response_body parsed as JSON dict
        """
        
        return {
            "test_case_id": self.test_case_id,
            "operation_id": self.operation_id,
            "path": self.path,
            "http_method": self.http_method,
            "parameters": self.parameters,
            "request_body": self.request_body,
            "status_code": self.status_code,
            "response_body": self.response_body
        }   
