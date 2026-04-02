"""Parameter values handling for dtrace generation.

Extracts parameter values from test cases for dtrace generation.

Author: Juan C. Alonso (Java), converted to Python
"""

from typing import Any, Dict, List, Optional
import json


def get_enter_parameter_value(test_case, hierarchy: List[str]) -> Optional[str]:
    """Get enter parameter value from various sources.
    
    Args:
        test_case: Test case object
        hierarchy: List of keys to search through
        
    Returns:
        Parameter value or None if not found
    """
    from agora.beet.variable.variable_utils import decode_variable_name
    from agora.beet.dtrace.variable_values import get_primitive_value_from_hierarchy
    from agora.beet.util.string_manager import decode_string
    
    query_parameters = test_case.get_query_parameters()
    path_parameters = test_case.get_path_parameters()
    header_parameters = test_case.get_header_parameters()
    form_parameters = test_case.get_form_parameters()
    body_parameter = test_case.get_body_parameter()
    
    value = None
    key = decode_variable_name(hierarchy[-1])
    
    # Try to find in different parameter sources
    value = get_parameter_value_from_source(query_parameters, key)
    if value is None:
        value = get_parameter_value_from_source(path_parameters, key)
    if value is None:
        value = get_parameter_value_from_source(header_parameters, key)
    if value is None:
        value = get_parameter_value_from_source(form_parameters, key)
    
    # Search in body parameter
    if value is None and body_parameter:
        try:
            json_body = json.loads(body_parameter)
            if json_body:
                hierarchy_body = hierarchy[1:]
                value = get_primitive_value_from_hierarchy(json_body, hierarchy_body)
        except (json.JSONDecodeError, TypeError):
            pass
    
    # Set value to None if it should be considered as null
    STRINGS_TO_CONSIDER_AS_NULL = ["null", "None", "", "undefined"]
    if value in STRINGS_TO_CONSIDER_AS_NULL:
        value = None
    
    return value


def get_parameter_value_from_source(source_parameters: Dict[str, str], key: str) -> Optional[str]:
    """Get parameter value from a specific source (query/path/header/form).
    
    If the key is not found, tries to find a URL encoded version.
    Example: "image[0]" → "image%5B0%5D"
    
    Args:
        source_parameters: Dictionary of parameters
        key: Parameter name to search for
        
    Returns:
        Parameter value or None if not found
    """
    from agora.beet.util.string_manager import encode_string
    
    value = source_parameters.get(key)
    
    # If not found, try encoded version
    if value is None:
        value = source_parameters.get(encode_string(key))
    
    return value


def get_value_of_parameter_for_dtrace_file(test_case, variable_name: str, 
                                           dec_type: str, rep_type: str) -> Optional[str]:
    """Get value of parameter for dtrace file (ENTER parameters).
    
    Args:
        test_case: Test case object
        variable_name: Name of the variable
        dec_type: Declaration type
        rep_type: Representation type
        
    Returns:
        Parameter value as string for dtrace, or None
    """
    from agora.beet.main.generate_instrumentation import PRIMITIVE_TYPES, STRING_TYPE_NAME, HIERARCHY_SEPARATOR
    from agora.beet.variable.variable_utils import decode_variable_name
    from agora.beet.util.string_manager import decode_string
    from agora.beet.dtrace.enter_array import generate_dtrace_enter_value_of_array
    
    value = None
    
    if dec_type in PRIMITIVE_TYPES:  # If primitive value
        # Get the variable name (without wrapping)
        hierarchy = variable_name.split(".")
        
        if len(hierarchy) > 1:
            value = get_enter_parameter_value(test_case, hierarchy)
        else:
            value = decode_variable_name(variable_name)
        
        if rep_type == STRING_TYPE_NAME and value:
            # Decode the parameter value (e.g., "street+address" → "street address", "1%2C2" → "1,2")
            value = decode_string(value)
            value = f'\"{value}\"'
    
    elif "[..]" in variable_name:  # If array values
        hierarchy = variable_name.replace("[..]", "").split(".")
        
        if len(hierarchy) > 1:
            # Get the array value (e.g., "element1%2Celement2%2Celement3")
            value = get_enter_parameter_value(test_case, hierarchy)
            
            if value:
                # Decode the value (e.g., "element1,element2,element3")
                value = decode_string(value)
                # Convert to array format
                value = generate_dtrace_enter_value_of_array(test_case, value, dec_type, variable_name)
            else:
                value = "nonsensical"
        else:
            value = variable_name
    
    else:  # If type = object or identifier of array
        value = f'\"{test_case.get_test_case_id()}{variable_name}input\"'
        value = value.replace(HIERARCHY_SEPARATOR, "").replace("_", "")
        value = str(abs(hash(value)))
        
        hierarchy = variable_name.split(".")
        if len(hierarchy) > 1:
            hierarchy = hierarchy[1:]
            key = get_enter_parameter_value(test_case, hierarchy)
            if key is None:
                value = None
    
    return value
