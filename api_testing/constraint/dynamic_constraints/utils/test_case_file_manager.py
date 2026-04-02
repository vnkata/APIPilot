"""Test case file management utilities for Beet."""

from typing import Dict, List, Optional
from . import csv_manager


class TestCaseFileManager:
    """Manages parsing of test case CSV files."""
    
    def __init__(self, header: str):
        """Initialize test case file manager.
        
        Args:
            header: Header line from CSV
        """
        record = csv_manager.get_csv_record(header)
        
        self.test_case_id_index = self._get_index_of_element(record, "testCaseId")
        self.operation_id_index = self._get_index_of_element(record, "operationId")
        self.path_index = self._get_index_of_element(record, "path")
        self.http_method_index = self._get_index_of_element(record, "httpMethod")
        self.header_parameters_index = self._get_index_of_element(record, "headerParameters")
        self.path_parameters_index = self._get_index_of_element(record, "pathParameters")
        self.query_parameters_index = self._get_index_of_element(record, "queryParameters")
        self.form_parameters_index = self._get_index_of_element(record, "formParameters")
        self.body_parameter_index = self._get_index_of_element(record, "bodyParameter")
        self.status_code_index = self._get_index_of_element(record, "statusCode")
        self.response_body_index = self._get_index_of_element(record, "responseBody")
    
    def get_test_case(self, row: List[str]) -> 'TestCase':
        """Parse a test case from CSV row.
        
        Args:
            row: CSV row as list of strings
            
        Returns:
            TestCase object
        """
        # Import here to avoid circular dependency
        from agora.beet.model import TestCase
        
        header_params = self._string_to_map(row[self.header_parameters_index])
        path_params = self._string_to_map(row[self.path_parameters_index])
        query_params = self._string_to_map(row[self.query_parameters_index])
        form_params = self._string_to_map(row[self.form_parameters_index])
        
        return TestCase(
            test_case_id=row[self.test_case_id_index],
            operation_id=row[self.operation_id_index],
            path=row[self.path_index],
            http_method=row[self.http_method_index],
            header_parameters=header_params,
            path_parameters=path_params,
            query_parameters=query_params,
            form_parameters=form_params,
            body_parameter=row[self.body_parameter_index],
            status_code=row[self.status_code_index],
            response_body=row[self.response_body_index]
        )
    
    @staticmethod
    def _get_index_of_element(record: List[str], header: str) -> int:
        """Find index of element in CSV header.
        
        Args:
            record: CSV header record
            header: Header name to find
            
        Returns:
            Index of header
            
        Raises:
            ValueError: If header not found
        """
        for i, col in enumerate(record):
            if col.lower() == header.lower():
                return i
        raise ValueError(f"Element {header} not found in the csv headers")
    
    @staticmethod
    def _string_to_map(str_val: str) -> Dict[str, str]:
        """Convert string representation to dict.
        
        Args:
            str_val: String like "key1=val1;key2=val2"
            
        Returns:
            Dictionary of key-value pairs
        """
        if not str_val or str_val.strip() == "":
            return {}
        
        result = {}
        for pair in str_val.split(";"):
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                value = remove_newline_chars(value)
                result[key] = value
        
        return result


def remove_newline_chars(s: str) -> str:
    """Remove newline characters from string.
    
    Args:
        s: Input string
        
    Returns:
        String with newlines replaced by escape sequences
    """
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    return s
