"""Test case model for Beet."""

from dataclasses import dataclass
import json
from typing import Dict, Optional

def cast_value(value):
    if isinstance(value, str):
        if "[" in value and "]" in value:
            try:
                json_str = value.replace("True", "true").replace("False", "false")
                val =  json.loads(json_str)
                if isinstance(val, list) and len(val) == 1:
                    return val[0]   
                return val
            except json.JSONDecodeError:
                pass
        if value.isdigit():
            return int(value)
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
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