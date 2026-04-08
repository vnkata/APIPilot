"""Exit variables handling for Beet.

Generates DeclsVariable declarations for API response exit/output variables.
Supports recursive traversal of nested objects and arrays in JSON responses.

Author: Juan C. Alonso (Java), converted to Python
"""

import json
from typing import List, Dict, Optional, Any, Union

from api_testing.constraint.dynamic_constraints.decls_variable import DeclsVariable
from api_testing.constraint.dynamic_constraints.variable.variable_utils import (
    translate_datatype, encode_variable_name, decode_variable_name,
    OBJECT_TYPE_NAME, ARRAY_TYPE_NAME, HASHCODE_TYPE_NAME,
    HIERARCHY_SEPARATOR, ARRAY_NESTING_SEPARATOR
)


def generate_decls_variables_of_exit(
    variable_name: str,
    var_kind: str,
    variable_name_output: str,
    map_of_properties: Optional[Dict]
) -> DeclsVariable:
    """Generate declarations variables for exit/output variables.
    
    Creates the father variable with no parent, and recursively generates
    son variables for all nested properties in the schema.
    
    Args:
        variable_name: Name of the variable
        var_kind: Kind of variable (e.g., "output", "field output")
        variable_name_output: Output variable name in dtrace format
        map_of_properties: Schema object or dictionary containing properties
        
    Returns:
        Root DeclsVariable with recursively generated enclosed variables
    """
    # This variable has no parentVariable
    father = DeclsVariable(
        variable_name,
        None,
        var_kind,
        variable_name_output,
        HASHCODE_TYPE_NAME,
        None
    )
    
    # Creates the son variables
    if map_of_properties:
        enclosed_vars = _generate_decls_variables_of_exit_recursive(
            map_of_properties, 
            variable_name, 
            var_kind, 
            variable_name_output, 
            False
        )
        father.enclosed_variables = enclosed_vars
    
    return father


def _generate_decls_variables_of_exit_recursive(
    map_of_properties: Union[Dict, Any],
    parent_variable: str,
    var_kind: str,
    variable_name_output: str,
    is_array: bool
) -> List[DeclsVariable]:
    """Recursively generate exit variables for nested properties.
    
    Processes object properties, arrays, and primitive types, creating
    corresponding DeclsVariable declarations for each.
    
    Args:
        map_of_properties: Schema object or dictionary containing properties
        parent_variable: Name of parent variable
        var_kind: Variable kind
        variable_name_output: Output variable name
        is_array: Whether operating on array element
        
    Returns:
        List of DeclsVariables for all properties
    """
    res: List[DeclsVariable] = []
    
    if map_of_properties is None:
        return res
    
    # Get properties from schema object or dictionary
    properties: Optional[Dict] = None
    
    # First, try to get properties as an attribute (for ItemProperties objects)
    if hasattr(map_of_properties, 'properties'):
        properties = getattr(map_of_properties, 'properties', None)
    
    # If not found, try dictionary access (for dict objects)
    if properties is None and isinstance(map_of_properties, dict):
        properties = map_of_properties.get('properties')
    
    # Warnings if properties == null
    if not properties:
        additional_props = None
        if hasattr(map_of_properties, 'additional_properties'):
            additional_props = getattr(map_of_properties, 'additional_properties', None)
        elif isinstance(map_of_properties, dict):
            additional_props = map_of_properties.get('additionalProperties')
        
        if additional_props is None:
            print(f"WARNING: No properties found for object: {parent_variable}")
        else:
            print(f"WARNING: Object: {parent_variable} only contains additional properties")
        return res
    
    # Process each property
    for param_name in properties.keys():
        schema = properties[param_name]
        
        # Get parameter type
        param_type = None
        if hasattr(schema, 'type'):
            param_type = getattr(schema, 'type', None)
        elif isinstance(schema, dict):
            param_type = schema.get('type')
        
        # If there is an allOf, parameterType is null, but the schema contains all the properties
        if param_type is None or (isinstance(param_type, str) and param_type.lower() == OBJECT_TYPE_NAME):
            # Object type - generate the father variable and recursively process children
            decls_variable = DeclsVariable(
                param_name,
                parent_variable,
                f"field {param_name}",
                f"{variable_name_output}{HIERARCHY_SEPARATOR}{encode_variable_name(param_name)}",
                HASHCODE_TYPE_NAME,
                parent_variable,
                is_array
            )
            
            # Recursive call for son variables
            enclosed_variables = _generate_decls_variables_of_exit_recursive(
                schema,
                f"{parent_variable}.{encode_variable_name(param_name)}",
                var_kind,
                variable_name_output,
                False
            )
            # Set enclosed variables
            decls_variable.enclosed_variables = enclosed_variables
            # Add to list
            res.append(decls_variable)
        
        elif isinstance(param_type, str) and param_type.lower() == ARRAY_TYPE_NAME:
            # Array type - obtain variables of nested arrays using NestedArrays handler
            # Note: This would call getDeclsVariablesOfNestedArray from nested_arrays module
            # For now, we'll import and use it if available
            try:
                from api_testing.constraint.dynamic_constraints.variable.nested_arrays import get_decls_variables_of_nested_array
                decls_variables = get_decls_variables_of_nested_array(
                    map_of_properties, 
                    parent_variable,
                    var_kind, 
                    param_name, 
                    variable_name_output
                )
                # Add to list
                res.extend(decls_variables)
            except ImportError:
                print(f"WARNING: Cannot import nested_arrays handler for array: {param_name}")
        
        else:
            # Primitive type - create simple variable
            translated_type = translate_datatype(param_type) if param_type else "int"
            
            decls_variable = DeclsVariable(
                param_name,
                parent_variable,
                f"field {param_name}",
                translated_type,
                translated_type,
                parent_variable,
                is_array
            )
            # Add to list
            res.append(decls_variable)
    
    return res


def generate_decls_variables_of_primitive_response(
    parameter_type: str,
    object_name: str,
    parent_variable: str,
    var_kind: str
) -> DeclsVariable:
    """Generate declarations for primitive response types.
    
    Used when the API response is a primitive type (e.g., String, int).
    This is generally a bad practice in API design but supported here.
    Used for both output and exit declarations.
    
    Args:
        parameter_type: Primitive parameter type (e.g., "int", "string")
        object_name: Name of the object variable
        parent_variable: Parent variable name
        var_kind: Variable kind
        
    Returns:
        DeclsVariable for primitive response
    """
    father = DeclsVariable(
        parent_variable,
        None,
        var_kind,
        object_name,
        HASHCODE_TYPE_NAME,
        None
    )
    
    translated_datatype = translate_datatype(parameter_type)
    
    enclosed_var = DeclsVariable(
        "primitive",
        parent_variable,
        "field primitive",
        translated_datatype,
        translated_datatype,
        parent_variable,
        False
    )
    
    father.enclosed_variables = [enclosed_var]
    
    return father


def get_list_of_json_elements_for_decls_exit(
    json_obj: Optional[Dict[str, Any]],
    element_route: List[str]
) -> List[Any]:
    """Get list of JSON elements for declarations exit.
    
    Traverses a JSON object following a route of property names and array
    indices, extracting the values at the target location.
    
    Args:
        json_obj: JSON object (dict) to traverse
        element_route: List of property names to follow (e.g., ["user", "addresses"])
        
    Returns:
        List of JSON elements found at the target location
        
    Raises:
        ValueError: If json_obj is None
    """
    if json_obj is None:
        raise ValueError("The response of the test case cannot be null")
    
    if not element_route:
        return []
    
    res: List[Any] = []
    element = decode_variable_name(element_route[0])
    
    # Check if the target element is a nested array
    element_array_route = [e.strip() for e in element.split(ARRAY_NESTING_SEPARATOR) if e.strip()]
    
    # If the target element is a nested array (contains ARRAY_NESTING_SEPARATOR)
    if len(element_array_route) > 1:
        # Get the nested arrays (i.e., value of the element)
        json_array = json_obj.get(element_array_route[0])
        
        if json_array and isinstance(json_array, list):
            # Count the target nesting level
            target_nesting_level = element.count(ARRAY_TYPE_NAME) + 1
            
            # Get JSON arrays of specified nesting level
            json_arrays = _get_json_arrays_of_specified_nesting_level(
                json_array, 
                target_nesting_level, 
                1
            )
            res.extend(json_arrays)
        
        return res
    
    # Get the first element value from JSON
    json_son = json_obj.get(element)
    
    if json_son is None:
        return res
    
    if isinstance(json_son, dict):
        # If jsonSon is of type dict (JSONObject)
        if len(element_route) == 1:
            # If element is the last element of elementRoute
            res.append(json_obj.get(element))
        else:
            # Recursive call if element is not the last element
            res.extend(get_list_of_json_elements_for_decls_exit(
                json_son,
                element_route[1:]
            ))
    
    elif isinstance(json_son, list):
        # If jsonSon is of type list (JSONArray)
        json_son_array = json_son
        
        # Iterate over all elements of the array
        for json_son_element in json_son_array:
            if isinstance(json_son_element, dict):
                if len(element_route) == 1:
                    res.append(json_son_element)
                else:
                    res.extend(get_list_of_json_elements_for_decls_exit(
                        json_son_element,
                        element_route[1:]
                    ))
            
            elif isinstance(json_son_element, list):
                # This condition is reached when dealing with nested arrays
                # Get all the properties of the nested array (flatten it)
                flat_list = _bubble_sort_flatten(json_son_element)
                res.extend(flat_list)
    
    return res


def _get_json_arrays_of_specified_nesting_level(
    json_array: List[Any],
    target_nesting_level: int,
    current_level: int
) -> List[List[Any]]:
    """Get JSON arrays at specified nesting level.
    
    Recursively traverses nested arrays to extract arrays at the target
    nesting depth.
    
    Args:
        json_array: Array to search
        target_nesting_level: The nesting level we're looking for
        current_level: Current level in recursion
        
    Returns:
        List of arrays at the target nesting level
    """
    res: List[List[Any]] = []
    
    if current_level == target_nesting_level:
        return [json_array]
    
    if not isinstance(json_array, list):
        return res
    
    for element in json_array:
        if isinstance(element, list):
            res.extend(_get_json_arrays_of_specified_nesting_level(
                element,
                target_nesting_level,
                current_level + 1
            ))
    
    return res


def _bubble_sort_flatten(json_array: List[Any]) -> List[Dict[str, Any]]:
    """Flatten nested arrays into list of objects.
    
    Recursively extracts all dictionaries from nested arrays.
    
    Args:
        json_array: Array potentially containing nested arrays and objects
        
    Returns:
        Flattened list of dictionary objects
    """
    res: List[Dict[str, Any]] = []
    
    for element in json_array:
        if isinstance(element, dict):
            res.append(element)
        elif isinstance(element, list):
            res.extend(_bubble_sort_flatten(element))
    
    return res

