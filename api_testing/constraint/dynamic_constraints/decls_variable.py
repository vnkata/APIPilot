"""Variable model for Beet."""

from dataclasses import dataclass, field
import time
from typing import List, Optional, Dict, Any
from .variable.variable_utils import (
    encode_variable_name, DOUBLE_TYPE_NAME, BOOLEAN_TYPE_NAME, INTEGER_TYPE_NAME,
    STRING_TYPE_NAME, ARRAY_TYPE_NAME, HIERARCHY_SEPARATOR, decode_variable_name, PRIMITIVE_TYPES
)
from .dtrace.parameter_values import get_value_of_parameter_for_dtrace_file
from .dtrace.variable_values import get_primitive_value_from_hierarchy, get_array_from_hierarchy
from .dtrace.exit_array import generate_dtrace_exit_value_of_json_array, remove_new_line_chars


# Constants
STRINGS_TO_CONSIDER_AS_NULL = ["null", "None", "", "undefined"]


@dataclass
class DeclsVariable:
    """Represents a variable declaration in Daikon format."""
    variable_name: str
    variable_path: Optional[str]
    var_kind: str
    dec_type: str
    rep_type: str
    enclosing_var: Optional[str] = None
    is_array: bool = False
    enclosed_variables: List['DeclsVariable'] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.variable_path:
            self.variable_name = f"{self.variable_path}.{encode_variable_name(self.variable_name)}"
        else:
            self.variable_name = encode_variable_name(self.variable_name)

        self.var_kind = encode_variable_name(self.var_kind)
        if self.dec_type == BOOLEAN_TYPE_NAME:
            self.rep_type = INTEGER_TYPE_NAME
        if self.is_array:
            self.dec_type = f"{self.dec_type}[]"
            self.rep_type = f"{self.rep_type}[]"

    def __str__(self) -> str:
        enclosing_var_str = f"\tenclosing-var {self.enclosing_var}\n" if self.enclosing_var else ""
        array_str = "\tarray 1\n" if self.is_array else ""

        output = (
            f"variable {self.variable_name}\n"
            f"\tvar-kind {self.var_kind}\n"
            f"{enclosing_var_str}"
            f"{array_str}"
            f"\tdec-type {self.dec_type}\n"
            f"\trep-type {self.rep_type}"
        )

        for var in self.enclosed_variables:
            output += f"\n{var}"

        return output

    def generate_dtrace_enter(self, test_case) -> str:
        """Generate dtrace enter content for this variable.
        
        Args:
            test_case: TestCase object
            
        Returns:
            Dtrace enter string
        """
        # Get value of parameter for dtrace file
        value = get_value_of_parameter_for_dtrace_file(
            test_case, self.variable_name, self.dec_type, self.rep_type
        )
        
        modified = "1"
        # If a value is nonsensical, the value of modified must be 2 instead of 1
        # A parameter of type double with a null value is nonsensical
        if (
            (self.rep_type.lower() == DOUBLE_TYPE_NAME or 
             self.rep_type.lower() == BOOLEAN_TYPE_NAME or 
             self.rep_type.lower() == INTEGER_TYPE_NAME) and
            (value is None or value == "null")
        ):
            value = "nonsensical"
            modified = "2"
        
        # This happens with arrays
        if value is not None and value == "nonsensical":
            modified = "2"
        #     time.sleep(200)  # sleep for 2 seconds
        # Convert value to string if not already
        if value is None:
            value = "null"
        elif isinstance(value, bool):
            value = int(value)
            
        # elif not isinstance(value, str):
        #     value = str(value)

        res = f"{self.variable_name}\n{value}\n{modified}"
        # Son variables (enclosed variables)
        for enclosed_var in self.enclosed_variables:
            res += f"\n{enclosed_var.generate_dtrace_enter(test_case)}"
        if self.variable_name == "input.Session" and value != "nonsensical":
            if "[" in res:
                print(res.replace("\n", "=>"),"", value)

        return res

    def generate_dtrace_exit(self, test_case, json_obj: Dict[str, Any], is_element_of_array: bool) -> str:
        """Generate dtrace exit content for this variable.
        
        Args:
            test_case: TestCase object
            json_obj: JSON response object
            is_element_of_array: Whether this is an element of an array
            
        Returns:
            Dtrace exit string
        """
        value = None
        is_nonsensical = False

        if (  # If primitive type
            self.dec_type in PRIMITIVE_TYPES and self.var_kind != ARRAY_TYPE_NAME
        ):
            # Get the variable name (without wrapping)
            hierarchy = self.variable_name.split(".")
            hierarchy = hierarchy[1:]  # Remove class name
            value = get_primitive_value_from_hierarchy(json_obj, hierarchy)


            if value in STRINGS_TO_CONSIDER_AS_NULL:
                value = None

            # Check if parent is None
            parent_hierarchy = hierarchy[:-1]
            if parent_hierarchy:
                parent_value = get_primitive_value_from_hierarchy(json_obj, parent_hierarchy)
                if parent_value is None:
                    value = "nonsensical"
                    is_nonsensical = True

            # Daikon does not support null values for parameters of type double
            # For this reason, if a null value is of type double, it is considered
            # nonsensical and the value of modified will be 2 instead of 1
            if (
                (self.rep_type.lower() == DOUBLE_TYPE_NAME or 
                 self.rep_type.lower() == INTEGER_TYPE_NAME or 
                 self.rep_type.lower() == BOOLEAN_TYPE_NAME) and
                value is None
            ):
                value = "nonsensical"
                # value = test_case.get_test_case_id()
                is_nonsensical = True
            if not is_nonsensical:
                if self.rep_type.replace("[]", "") == STRING_TYPE_NAME and value is not None:
                    # Replace new line characters from the string
                    value = remove_new_line_chars(value)
                    value = f'"{value}"'

                if is_element_of_array:
                        value = f"[{value}]"
            
        elif self.var_kind == ARRAY_TYPE_NAME:  # If array
            hierarchy = self.variable_name.replace("[..]", "").split(".")
            hierarchy = hierarchy[1:]  # Remove the class name from the hierarchy
            elements = get_array_from_hierarchy(json_obj, hierarchy)

            # If elements == None, the elements are set to nonsensical
            value = generate_dtrace_exit_value_of_json_array(
                test_case, elements, self.dec_type, self.variable_name
            )
            if value == "nonsensical":
                is_nonsensical = True

        else:  # If type = object or identifier of array (both array of objects and array of primitives)
            # Use a hashcode as value
            value = f'"{test_case.test_case_id}{self.variable_name}output"'
            value = value.replace(HIERARCHY_SEPARATOR, "").replace("_", "")
            value = str(abs(hash(value)))

            # If the element (either array or object) is not present in the response JSON,
            # we set its value to nonsensical
            hierarchy = self.variable_name.split(".")
            hierarchy = hierarchy[1:]
            if hierarchy:  # hierarchy.size()==0 is the "return" object
                key = get_primitive_value_from_hierarchy(json_obj, hierarchy)
                if key is None:
                    value = "nonsensical"
                    is_nonsensical = True

            if is_element_of_array:
                value = f"[{value}]"

        # Build result
        modified = "2" if is_nonsensical else "1"
        # if isinstance(value, bool) and value != "nonsensical":
        #     value = int(value)
        # Convert value to string if not already
        if value is None:
            value = "null"
        elif isinstance(value, bool):
            value = int(value)
        # elif not isinstance(value, str):
        #     value = str(value)
        res = f"{self.variable_name}\n{value}\n{modified}"

        # Son variables (enclosed variables)
        for enclosed_var in self.enclosed_variables:
            if self.var_kind == ARRAY_TYPE_NAME:
                hierarchy = self.variable_name.replace("[..]", "").split(".")
                key = decode_variable_name(hierarchy[-1])
                elements = json_obj.get(key)

                if isinstance(elements, list) and elements:
                    # Use first element as in Java code (elements.get(0))
                    element = elements[0]
                    if isinstance(element, dict):
                        res += f"\n{enclosed_var.generate_dtrace_exit(test_case, element, True)}"
            else:  # The element was an object or primitive
                res += f"\n{enclosed_var.generate_dtrace_exit(test_case, json_obj, False)}"
        # if test_case.get_test_case_id() == "54f4cd98-4fca-4468-9123-04ac7643ceb3":
        #     print(res)
        return res
