"""Enter array handling for dtrace generation.

Generates dtrace enter values for array types.

Author: Juan C. Alonso (Java), converted to Python
"""

import ast
import json
from typing import Any, List, Optional

from api_testing.constraint.dynamic_constraints.variable.variable_utils import STRING_TYPE_NAME
from api_testing.constraint.dynamic_constraints.dtrace.exit_array import generate_dtrace_exit_value_of_json_array


def _normalize_array_elements(elements: Any) -> Optional[List[Any]]:
    if elements is None:
        return None

    if isinstance(elements, list):
        return elements

    if isinstance(elements, tuple):
        return list(elements)

    if not isinstance(elements, str):
        return [elements]

    stripped_elements = elements.strip()
    if not stripped_elements:
        return None

    if stripped_elements.startswith("[") and stripped_elements.endswith("]"):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed_value = parser(stripped_elements)
                if isinstance(parsed_value, list):
                    return parsed_value
            except (ValueError, SyntaxError, json.JSONDecodeError, TypeError):
                continue

    return None


def generate_dtrace_enter_value_of_array(test_case, elements: Any, dectype: str, variable_name: str) -> str:
    """Generate dtrace enter value for an array.
    
    Converts comma-separated input elements into a JSON array and calls 
    generate_dtrace_exit_value_of_json_array to generate the proper dtrace format.
    
    Args:
        test_case: TestCase object
        elements: Comma-separated array elements (e.g., "elem1,elem2,elem3")
        dectype: Declaration type (e.g., "int[]", "String[]")
        variable_name: Name of the array variable
        
    Returns:
        Dtrace format string for the array, or "nonsensical" if parsing fails
    """
    normalized_elements = _normalize_array_elements(elements)
    if normalized_elements is not None:
        return generate_dtrace_exit_value_of_json_array(
            test_case,
            normalized_elements,
            dectype,
            variable_name,
        )

    if isinstance(elements, str):
        elements = elements.strip()
    if not elements:
        return "nonsensical"
    
    # Convert the input into a JSON array
    value_array: Optional[List[Any]] = None
    base_type = dectype.replace("[]", "")
    
    try:
        if base_type == STRING_TYPE_NAME:
            # Add double quotes to all array elements if they are of type string
            # Handle empty strings and commas properly
            if elements.strip() == ",":
                # Special case: single empty string
                json_str = '[""]'
            else:
                # Split by comma and wrap each element in quotes
                parts = [part.strip() for part in elements.split(",")]
                json_str = '["' + '","'.join(parts) + '"]'
        else:
            # For non-string types, assume elements are already properly formatted
            json_str = f'[{elements}]'
        
        value_array = json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        # If parsing fails, return nonsensical
        return "nonsensical"
    
    return generate_dtrace_exit_value_of_json_array(test_case, value_array, dectype, variable_name)
