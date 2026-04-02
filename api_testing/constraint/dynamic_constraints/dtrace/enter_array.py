"""Enter array handling for dtrace generation.

Generates dtrace enter values for array types.

Author: Juan C. Alonso (Java), converted to Python
"""

from typing import List
import json


def generate_dtrace_enter_value_of_array(test_case, elements: str, dectype: str, variable_name: str) -> str:
    """Generate dtrace enter value for an array.
    
    Converts input elements into a JSONArray and calls generate_dtrace_exit_value_of_json_array
    to generate the proper dtrace format.
    
    Args:
        test_case: Test case object
        elements: Comma-separated array elements
        dectype: Declaration type (e.g., "int[]", "String[]")
        variable_name: Name of the array variable
        
    Returns:
        Dtrace format string for the array
    """
    from agora.beet.main.generate_instrumentation import STRING_TYPE_NAME
    from agora.beet.dtrace.exit_array import generate_dtrace_exit_value_of_json_array
    
    # Convert the input into a JSON array
    value_array = None
    base_type = dectype.replace("[]", "")
    
    if base_type == STRING_TYPE_NAME:
        # Add double quotes to all array elements if they are of type string
        json_str = '["' + elements.replace(",", '","') + '"]'
    else:
        json_str = '[' + elements + ']'
    
    try:
        value_array = json.loads(json_str)
    except json.JSONDecodeError:
        value_array = None
    
    return generate_dtrace_exit_value_of_json_array(test_case, value_array, dectype, variable_name)
