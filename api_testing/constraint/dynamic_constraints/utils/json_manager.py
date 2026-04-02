"""JSON management utilities for Beet."""

import json
from typing import Any, Union


def string_to_json_array(input_str: str) -> list:
    """Convert string to JSON array.
    
    Args:
        input_str: JSON string
        
    Returns:
        Parsed JSON array
        
    Raises:
        json.JSONDecodeError: If parsing fails
    """
    try:
        result = json.loads(input_str)
        if not isinstance(result, list):
            raise ValueError("Expected JSON array")
        return result
    except json.JSONDecodeError as e:
        print("Error converting the response body to string")
        raise


def string_to_json_object(input_str: str) -> dict:
    """Convert string to JSON object.
    
    Args:
        input_str: JSON string
        
    Returns:
        Parsed JSON object
        
    Raises:
        json.JSONDecodeError: If parsing fails
    """
    try:
        result = json.loads(input_str)
        if not isinstance(result, dict):
            raise ValueError("Expected JSON object")
        return result
    except json.JSONDecodeError as e:
        print("Error converting the response body to string")
        raise


def is_string_json_array(input_str: str) -> bool:
    """Check if string is a valid JSON array.
    
    Args:
        input_str: JSON string to check
        
    Returns:
        True if valid JSON array, False otherwise
    """
    try:
        result = json.loads(input_str)
        return isinstance(result, list)
    except json.JSONDecodeError:
        return False
