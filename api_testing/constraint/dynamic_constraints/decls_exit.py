"""DeclsExit model for Beet."""

from typing import TYPE_CHECKING, Optional, List, Any
from unittest import TestCase

from api_testing.constraint.dynamic_constraints.decls_enter import DeclsEnter
from api_testing.constraint.dynamic_constraints.decls_variable import DeclsVariable
from api_testing.constraint.dynamic_constraints.dtrace.exit_array import generate_dtrace_exit_value_of_json_array
from api_testing.constraint.dynamic_constraints.utils.array_nesting_manager import do_bubble_sort, get_json_arrays_of_specified_nesting_level
from api_testing.constraint.dynamic_constraints.utils.json_manager import is_string_json_array, string_to_json_array, string_to_json_object
from api_testing.constraint.dynamic_constraints.variable.array_variables import generate_decls_variables_of_array_exit
from api_testing.constraint.dynamic_constraints.variable.exit_variables import generate_decls_variables_of_exit, generate_decls_variables_of_primitive_response
from api_testing.constraint.dynamic_constraints.variable.variable_utils import ARRAY_NESTING_SEPARATOR, HIERARCHY_SEPARATOR
from api_testing.models.specification_model import ItemProperties


def get_list_of_json_elements_for_decls_exit(data: Any, route: List[str]) -> List[Any]:
    """Navigate a JSON object/list to find all elements for the exit route.

    Args:
        data: JSON object or list to traverse
        route: Route path segments (after splitting on HIERARCHY_SEPARATOR)

    Returns:
        List of matching nested elements.
    """
    if not route:
        return [data]

    head, *tail = route
    if isinstance(data, dict):
        if head not in data:
            return []

        next_node = data[head]

        if not tail:
            if isinstance(next_node, list):
                return next_node
            return [next_node]

        if isinstance(next_node, list):
            results: List[Any] = []
            for item in next_node:
                results.extend(get_list_of_json_elements_for_decls_exit(item, tail))
            return results

        return get_list_of_json_elements_for_decls_exit(next_node, tail)

    if isinstance(data, list):
        results: List[Any] = []
        for item in data:
            results.extend(get_list_of_json_elements_for_decls_exit(item, route))
        return results

    return []


class DeclsExit:
    """Represents an exit program point in Daikon format."""

    _exit_counter = 1

    def __init__(
        self,
        endpoint: str,
        operation_name: str,
        variable_name_input: str,
        enter_decls_variables: 'DeclsVariable',
        variable_name_output: str,
        schema_or_type: Any,
        name_suffix: str,
        status_code: str,
        variable_name: Optional[str] = None,
    ):
        """Initialize DeclsExit."""
        self.endpoint = endpoint
        self.operation_name = operation_name
        self.variable_name_input = variable_name_input
        self.name_suffix = name_suffix
        self.status_code = status_code

        self.exit_number = DeclsExit._exit_counter
        DeclsExit._exit_counter += 1

        self.enter_decls_variables = enter_decls_variables
        self.is_nested_array = False

        # Determine behaviour based on schema_or_type
        self.exit_decls_variables = None
        if isinstance(schema_or_type, str) and variable_name is None:
            # Primitive response path
            self.name_suffix = ""
            self.is_nested_array = False
            self.exit_decls_variables = generate_decls_variables_of_primitive_response(
                schema_or_type,
                variable_name_output,
                "return",
                "return",
            )

        elif isinstance(schema_or_type, ItemProperties) and schema_or_type is not None:
            # Object or array schema path
            schema_type = getattr(schema_or_type, "type", None)
            if schema_type and schema_type.lower() == "array":
                self.is_nested_array = True
                self.exit_decls_variables = generate_decls_variables_of_array_exit(
                    schema_or_type,
                    variable_name_output + name_suffix,
                    "return",
                    "return",
                    None,
                )
            else:
                self.is_nested_array = False
                self.exit_decls_variables = generate_decls_variables_of_exit(
                    "return",
                    "return",
                    variable_name_output + name_suffix,
                    schema_or_type,
                )

        else:
            # fallback
            self.is_nested_array = False
            self.exit_decls_variables = None

    @classmethod
    def from_object_schema(
        cls,
        endpoint: str,
        operation_name: str,
        variable_name_input: str,
        enter_variables: 'DeclsVariable',
        variable_name_output: str,
        map_of_properties: Any,
        name_suffix: str,
        status_code: str,
    ) -> 'DeclsExit':
        return cls(
            endpoint,
            operation_name,
            variable_name_input,
            enter_variables,
            variable_name_output,
            map_of_properties,
            name_suffix,
            status_code,
            None,
        )

    @classmethod
    def from_array_schema(
        cls,
        endpoint: str,
        operation_name: str,
        variable_name_input: str,
        enter_variables: 'DeclsVariable',
        variable_name_output: str,
        array_schema: Any,
        variable_name: str,
        name_suffix: str,
        status_code: str,
    ) -> 'DeclsExit':
        return cls(
            endpoint,
            operation_name,
            variable_name_input,
            enter_variables,
            variable_name_output,
            array_schema,
            name_suffix,
            status_code,
            variable_name,
        )

    @classmethod
    def from_primitive_type(
        cls,
        endpoint: str,
        operation_name: str,
        variable_name_input: str,
        enter_variables: 'DeclsVariable',
        variable_name_output: str,
        parameter_type: str,
        status_code: str,
    ) -> 'DeclsExit':
        return cls(
            endpoint,
            operation_name,
            variable_name_input,
            enter_variables,
            variable_name_output,
            parameter_type,
            "",
            status_code,
            None,
        )

    def get_exit_name(self) -> str:
        """Get the exit program point name in Daikon style."""
        return (
            f"{self.endpoint}{HIERARCHY_SEPARATOR}{self.operation_name}"
            f"{HIERARCHY_SEPARATOR}{self.status_code}{self.name_suffix}()"
        )

    def __str__(self) -> str:
        res = f"ppt {self.get_exit_name()}:::EXIT{self.exit_number}\n"
        res += "ppt-type subexit\n"
        res += f"{self.enter_decls_variables}\n" if self.enter_decls_variables else ""
        res += f"{self.exit_decls_variables}" if self.exit_decls_variables else ""
        return res

    def generate_dtrace(self, test_case: 'TestCase', decls_enter: 'DeclsEnter') -> str:
        """Generate dtrace representation for this exit."""
        res = ""
        response_body = test_case.response_body

        if is_string_json_array(response_body):
            json_array = string_to_json_array(response_body)

            if self.is_nested_array:
                target_nesting_level = (
                    self.name_suffix.split(ARRAY_NESTING_SEPARATOR).count("array")
                )
                json_arrays_to_generate_dtrace = get_json_arrays_of_specified_nesting_level(
                    json_array,
                    target_nesting_level,
                    1,
                )
                for element in json_arrays_to_generate_dtrace:
                    res += self.generate_single_dtrace_enter_and_exit_array(
                        element, test_case, decls_enter
                    )

            else:
                flat_list = do_bubble_sort(json_array)
                res += self.generate_single_dtrace_enter_and_exit(
                    flat_list, test_case, decls_enter
                )

        else:

            json_obj = string_to_json_object(response_body)
            res += self.generate_single_dtrace_enter_and_exit(
                [json_obj], test_case, decls_enter
            )

        return res

    def generate_single_dtrace_enter_and_exit(
        self,
        json_object_list: List[Any],
        test_case: 'TestCase',
        decls_enter: 'DeclsEnter',
    ) -> str:
        res = ""

        for entry in json_object_list:
            element_route = [
                e
                for e in self.name_suffix.split(HIERARCHY_SEPARATOR)
                if e.strip()
            ]

            nested_json_objects = []
            if not element_route:
                nested_json_objects.append(entry)
            else:
                nested_json_objects = get_list_of_json_elements_for_decls_exit(
                    entry, element_route
                )

            for json_element in nested_json_objects:
                if isinstance(json_element, dict):
                    res += decls_enter.generate_dtrace(test_case) + "\n"
                    res += self.generate_single_dtrace_exit(test_case, json_element)
                elif isinstance(json_element, list):
                    res += self.generate_single_dtrace_enter_and_exit_array(
                        json_element, test_case, decls_enter
                    )

        return res

    def generate_single_dtrace_enter_and_exit_array(
        self,
        json_array: List[Any],
        test_case: 'TestCase',
        decls_enter: 'DeclsEnter',
    ) -> str:
        res = ""
        res += decls_enter.generate_dtrace(test_case) + "\n"
        res += self.generate_single_dtrace_exit_array(test_case, json_array)
        return res

    def generate_single_dtrace_exit_array(
        self,
        test_case: 'TestCase',
        json_array: List[Any],
    ) -> str:
        res = f"{self.get_exit_name()}:::EXIT{self.exit_number}"
        res += "\n" + self.enter_decls_variables.generate_dtrace_enter(test_case) + "\n"

        # Group 1
        res += "return\n"
        v = f'"{test_case.get_test_case_id()}{self.operation_name}returnoutput"'
        v = v.replace(HIERARCHY_SEPARATOR, "").replace("_", "")
        res += str(abs(hash(v))) + "\n"
        res += "1\n"

        # Group 2
        res += "return.array\n"
        value = generate_dtrace_exit_value_of_json_array(
            test_case,
            json_array,
            self.exit_decls_variables.enclosed_variables[0].dec_type
            if self.exit_decls_variables and self.exit_decls_variables.enclosed_variables
            else "",
            "array",
        )
        if value == "nonsensical":
            res += "null\n"
        else:
            v1 = f'"{test_case.get_test_case_id()}{self.operation_name}return{self.name_suffix}output"'
            v1 = v1.replace(HIERARCHY_SEPARATOR, "").replace("_", "")
            res += str(abs(hash(v1))) + "\n"
        res += "1\n"

        # Group 3
        res += "return.array[..]\n"
        res += value + "\n"
        modified = "2" if value == "nonsensical" else "1"
        res += modified + "\n\n"

        return res

    def generate_single_dtrace_exit(
        self,
        test_case: 'TestCase',
        json_element: dict,
    ) -> str:
        res = f"{self.get_exit_name()}:::EXIT{self.exit_number}"
        res += "\n" + self.enter_decls_variables.generate_dtrace_enter(test_case)
        res += "\n" + self.exit_decls_variables.generate_dtrace_exit(
            test_case,
            json_element,
            False,
        )
        res += "\n\n"
        return res

    @classmethod
    def reset_exit_counter(cls) -> None:
        """Reset the exit counter. Useful for testing."""
        cls._exit_counter = 1
