"""Exit array handling for dtrace generation.

Generates dtrace exit values for JSON arrays containing primitives or objects.

Author: Juan C. Alonso (Java), converted to Python
"""

from typing import List, Any, Optional

from api_testing.constraint.dynamic_constraints.variable.variable_utils import HIERARCHY_SEPARATOR, PRIMITIVE_TYPES, STRING_TYPE_NAME


class ExitArrayHandler:
    """Handles dtrace exit value generation for JSON arrays."""
    
    # Strings to consider as null values
    STRINGS_TO_CONSIDER_AS_NULL = ["null", "None", "", "undefined"]
    
    @staticmethod
    def remove_new_line_chars(value: Any) -> str:
        """Escape newline characters for Daikon dtrace values.
        
        Args:
            value: String value to escape
            
        Returns:
            Escaped string with newlines replaced
        """
        if value is None:
            return ""
        string_value = value if isinstance(value, str) else str(value)
        return string_value.replace("\n", "\\n").replace("\r", "\\r")
    
    @staticmethod
    def generate_dtrace_exit_value_of_json_array(test_case, elements: Optional[List[Any]], 
                                                 dectype: str, variable_name: str) -> str:
        """Generate dtrace exit value for a JSON array.
        
        Formats array elements as dtrace values. For primitives, returns formatted list.
        For objects, returns list of hashcodes.
        
        Args:
            test_case: Test case object containing test execution data
            elements: List of array elements, or None if array is empty/null
            dectype: Declaration type (e.g., "int[]", "String[]", "Object[]")
            variable_name: Name of the array variable for hashcode generation
            
        Returns:
            Dtrace format string for the array, or "nonsensical" if invalid
        """
        value = "nonsensical"
        # If elements is None, they are set to nonsensical
        if elements is not None:
            base_type = dectype.replace("[]", "")
            
            if base_type in PRIMITIVE_TYPES:  # If array of primitives
                is_string = base_type == STRING_TYPE_NAME
                value_parts = []
                
                for element in elements:
                    if is_string:
                        if element is None or str(element) in ExitArrayHandler.STRINGS_TO_CONSIDER_AS_NULL:
                            value_parts.append("null")
                        else:
                            cleaned = ExitArrayHandler.remove_new_line_chars(str(element))
                            value_parts.append(f'"{cleaned}"')
                    else:
                        # For non-string primitives, convert to string representation
                        if element is None:
                            value_parts.append("null")
                        else:
                            value_parts.append(str(element))
                
                value = "[" + " ".join(value_parts) + "]"
            
            else:  # If array of objects
                hashcode_parts = []
                
                for i, element in enumerate(elements, 1):
                    if element is not None:
                        # Generate hashcode from test case ID and variable name
                        cleaned_variable_name = variable_name.replace("[..]", "")
                        hash_input = f"{test_case.get_test_case_id()}{HIERARCHY_SEPARATOR}{cleaned_variable_name}{HIERARCHY_SEPARATOR}output{HIERARCHY_SEPARATOR}{i}"
                        hash_input = hash_input.replace(HIERARCHY_SEPARATOR, "").replace("_", "")
                        hashcode_parts.append(str(abs(hash(hash_input))))
                    else:
                        hashcode_parts.append("null")
                
                value = "[" + " ".join(hashcode_parts) + "]"
        # if elements is None and value == "nonsensical":
        #     value = []
            #
            #  print(f"Warning: Could not generate dtrace exit value for variable '{variable_name}' with declaration type '{dectype}' and elements: {elements}")
        return value


# Backward compatibility - keep the original function as a wrapper
def remove_new_line_chars(value: Any) -> str:
    """Escape newline characters for Daikon dtrace values."""
    return ExitArrayHandler.remove_new_line_chars(value)


def generate_dtrace_exit_value_of_json_array(test_case, elements: Optional[List[Any]], 
                                             dectype: str, variable_name: str) -> str:
    """Generate dtrace exit value for a JSON array.
    
    This is a backward compatibility wrapper around ExitArrayHandler.
    """
    return ExitArrayHandler.generate_dtrace_exit_value_of_json_array(
        test_case, elements, dectype, variable_name
    )
