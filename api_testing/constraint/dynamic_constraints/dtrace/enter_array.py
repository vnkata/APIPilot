"""Enter array handling for dtrace generation.

Generates dtrace enter values for array types.

Author: Juan C. Alonso (Java), converted to Python
"""

import json
from typing import List, Any, Optional

from api_testing.constraint.dynamic_constraints.variable.variable_utils import STRING_TYPE_NAME
from api_testing.constraint.dynamic_constraints.dtrace.exit_array import generate_dtrace_exit_value_of_json_array


def generate_dtrace_enter_value_of_array(test_case, elements: str, dectype: str, variable_name: str) -> str:
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
    if not elements or not elements.strip():
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
    except (json.JSONDecodeError, ValueError) as e:
        # If parsing fails, return nonsensical
        print(f"Warning: Failed to parse array elements '{elements}' for type {dectype}: {e}")
        return "nonsensical"
    
    return generate_dtrace_exit_value_of_json_array(test_case, value_array, dectype, variable_name)
