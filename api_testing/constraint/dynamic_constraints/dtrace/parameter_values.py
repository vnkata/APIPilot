"""Parameter values handling for dtrace generation.

Extracts parameter values from test cases for dtrace generation.

Author: Juan C. Alonso (Java), converted to Python
"""

import json
from typing import Any, Dict, List, Optional

from api_testing.constraint.dynamic_constraints.variable.variable_utils import (
    BOOLEAN_TYPE_NAME, DOUBLE_TYPE_NAME, HIERARCHY_SEPARATOR, INTEGER_TYPE_NAME,
    PRIMITIVE_TYPES, STRING_TYPE_NAME, decode_variable_name
)
from api_testing.constraint.dynamic_constraints.dtrace.variable_values import get_primitive_value_from_hierarchy
from api_testing.constraint.dynamic_constraints.utils.string_manager import decode_string, encode_string
from api_testing.constraint.dynamic_constraints.dtrace.enter_array import generate_dtrace_enter_value_of_array


TRUTHY_VALUES = {"true", "yes", "on", "1"}
FALSY_VALUES = {"false", "no", "off", "0"}


def _unwrap_single_value_container(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]

    if isinstance(value, dict) and len(value) == 1:
        key, nested_value = next(iter(value.items()))
        if str(key).lower() in {"val", "value"}:
            return nested_value

    return value


def _coerce_primitive_value_for_rep_type(value: Any, rep_type: str) -> Any:
    value = _unwrap_single_value_container(value)
    base_rep_type = rep_type.replace("[]", "").lower()

    if base_rep_type == STRING_TYPE_NAME or value is None:
        return value

    if base_rep_type in {BOOLEAN_TYPE_NAME, INTEGER_TYPE_NAME}:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            normalized_value = decode_string(value).strip().lower()
            if normalized_value in TRUTHY_VALUES:
                return 1
            if normalized_value in FALSY_VALUES:
                return 0
            try:
                return int(normalized_value)
            except ValueError:
                return "nonsensical"
        return "nonsensical"

    if base_rep_type == DOUBLE_TYPE_NAME:
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            normalized_value = decode_string(value).strip().lower()
            if normalized_value in TRUTHY_VALUES:
                return 1.0
            if normalized_value in FALSY_VALUES:
                return 0.0
            try:
                return float(normalized_value)
            except ValueError:
                return "nonsensical"
        return "nonsensical"

    return value
    
def get_enter_parameter_value(test_case, hierarchy: List[str]) -> Optional[str]:
    """Get enter parameter value from various sources.
    
    Args:
        test_case: TestCase object
        hierarchy: List of keys to search through
        
    Returns:
        Parameter value or None if not found
    """
    value = None
    key = decode_variable_name(hierarchy[-1])
    
    # Try to find in parameters (query/path/header/form)
    value = test_case.parameters.get(key)
    # Search in request body
    if value is None and test_case.request_body:
        try:
            if isinstance(test_case.request_body, str):
                json_body = json.loads(test_case.request_body)
            else:
                json_body = test_case.request_body
            
            if json_body and isinstance(json_body, dict):
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
    value = source_parameters.get(key)
    
    # If not found, try encoded version
    if value is None:
        value = source_parameters.get(encode_string(key))
    
    return value


def get_value_of_parameter_for_dtrace_file(test_case, variable_name: str, 
                                           dec_type: str, rep_type: str) -> Optional[str]:
    """Get value of parameter for dtrace file (ENTER parameters).
    
    Args:
        test_case: TestCase object
        variable_name: Name of the variable
        dec_type: Declaration type
        rep_type: Representation type
        
    Returns:
        Parameter value as string for dtrace, or None
    """
    value = None
    
    if dec_type in PRIMITIVE_TYPES:  # If primitive value
        # Get the variable name (without wrapping)
        hierarchy = variable_name.split(".")
        if len(hierarchy) > 1:
            value = get_enter_parameter_value(test_case, hierarchy)
        else:
            value = decode_variable_name(variable_name)

        value = _coerce_primitive_value_for_rep_type(value, rep_type)
        
        if rep_type == STRING_TYPE_NAME and value is not None:
            # Decode the parameter value (e.g., "street+address" → "street address", "1%2C2" → "1,2")
            value = decode_string(value) if isinstance(value, str) else str(value)
            value = f'\"{value}\"'
        elif value is not None and isinstance(value, str):
            # For non-string primitive types, if value is a string that should be quoted
            # (like "None", "null", etc.), we need to quote it to avoid Daikon warnings
            STRINGS_TO_QUOTE = ["None", "null", "undefined"]
            if value in STRINGS_TO_QUOTE:
                value = f'\"{value}\"'
    
    elif "[..]" in variable_name:  # If array values
        hierarchy = variable_name.replace("[..]", "").split(".")
        if len(hierarchy) > 1:
            # Get the array value (e.g., "element1%2Celement2%2Celement3")
            value = get_enter_parameter_value(test_case, hierarchy)
            if value:
                # Decode the value (e.g., "element1,element2,element3")
                value = decode_string(value) if isinstance(value, str) else value
                # Convert to array format
                value = generate_dtrace_enter_value_of_array(test_case, value, dec_type, variable_name)
            else:
                value = "nonsensical"
        else:
            value = variable_name
    
    else:  # If type = object or identifier of array
        value = f'\"{test_case.test_case_id}{variable_name}input\"'
        value = value.replace(HIERARCHY_SEPARATOR, "").replace("_", "")
        value = str(abs(hash(value)))
        
        hierarchy = variable_name.split(".")
        if len(hierarchy) > 1:
            hierarchy = hierarchy[1:]
            key = get_enter_parameter_value(test_case, hierarchy)
            if key is None:
                value = None
    
    return value
    
