"""Exit array handling for dtrace generation.

Generates dtrace exit values for JSON arrays containing primitives or objects.

Author: Juan C. Alonso (Java), converted to Python
"""

from typing import List, Any, Optional

from api_testing.constraint.dynamic_constraints.variable.variable_utils import HIERARCHY_SEPARATOR, PRIMITIVE_TYPES, STRING_TYPE_NAME


def remove_new_line_chars(value: str) -> str:
    """Escape newline characters for Daikon dtrace values."""
    if value is None:
        return ""
    return value.replace("\n", "\\n").replace("\r", "\\r")


def generate_dtrace_exit_value_of_json_array(test_case, elements: Optional[List[Any]], 
                                             dectype: str, variable_name: str) -> str:
    """Generate dtrace exit value for a JSON array.
    
    Formats array elements as dtrace values. For primitives, returns formatted list.
    For objects, returns list of hashcodes.
    
    Args:
        test_case: Test case object
        elements: List of array elements, or None
        dectype: Declaration type (e.g., "int[]", "String[]")
        variable_name: Name of the array variable
        
    Returns:
        Dtrace format string for the array
    """
    
    # Import the strings to consider as null
    STRINGS_TO_CONSIDER_AS_NULL = ["null", "None", "", "undefined"]
    
    value = "nonsensical"
    
    # If elements == None, they are set to nonsensical
    if elements is not None:
        base_type = dectype.replace("[]", "")
        
        if base_type in PRIMITIVE_TYPES:  # If array of primitives
            is_string = base_type == STRING_TYPE_NAME
            value_parts = []
            
            for element in elements:
                if is_string:
                    if element is None or str(element) in STRINGS_TO_CONSIDER_AS_NULL:
                        value_parts.append("null")
                    else:
                        cleaned = remove_new_line_chars(str(element))
                        value_parts.append(f'\"{cleaned}\"')
                else:
                    value_parts.append(str(element))
            
            value = "[" + " ".join(value_parts) + "]"
        
        else:  # If array of objects
            hashcode_parts = []
            
            for i, element in enumerate(elements, 1):
                if element is not None:
                    # Generate hashcode from test case ID and variable name
                    cleaned_variable_name = variable_name.replace("[..]", "")
                    v = f"\"{test_case.get_test_case_id()}{HIERARCHY_SEPARATOR}{cleaned_variable_name}{HIERARCHY_SEPARATOR}output{HIERARCHY_SEPARATOR}{i}\""
                    v = v.replace(HIERARCHY_SEPARATOR, "").replace("_", "")
                    hashcode_parts.append(str(abs(hash(v))))
                else:
                    hashcode_parts.append("null")
            
            value = "[" + " ".join(hashcode_parts) + "]"
    
    return value
