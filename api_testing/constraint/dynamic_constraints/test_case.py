"""Test case model for Beet."""

from typing import Dict, Optional


class TestCase:
    """Represents a test case from API calls."""
    
    def __init__(
        self,
        test_case_id: str,
        operation_id: str,
        path: str,
        http_method: str,
        parameters: Optional[Dict[str, str]] = None,
        status_code: Optional[str] = None,
        response_body: Optional[str] = None
    ):
        """Initialize a TestCase.
        
        Args:
            test_case_id: ID of the test case
            operation_id: ID of the operation
            path: API path
            http_method: HTTP method
            header_parameters: Header parameters
            path_parameters: Path parameters
            query_parameters: Query parameters
            form_parameters: Form parameters
            body_parameter: Request body
            status_code: Response status code
            response_body: Response body
        """
        self.test_case_id = test_case_id
        self.operation_id = operation_id
        self.path = path
        self.http_method = http_method
        self.header_parameters = header_parameters or {}
        self.path_parameters = path_parameters or {}
        self.query_parameters = query_parameters or {}
        self.form_parameters = form_parameters or {}
        self.body_parameter = body_parameter
        self.status_code = status_code
        self.response_body = response_body
 