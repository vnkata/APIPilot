"""Nested arrays handling for Beet."""

from typing import List, Dict
from api_testing.constraint.dynamic_constraints.decls_variable import DeclsVariable
from api_testing.constraint.dynamic_constraints.variable.variable_utils import (
    translate_datatype, OBJECT_TYPE_NAME, ARRAY_TYPE_NAME, HASHCODE_TYPE_NAME
)
from api_testing.constraint.dynamic_constraints.variable.array_variables import get_decls_variables_array


def get_decls_variables_of_nested_array(
    map_of_properties: Dict,
    variable_path: str,
    var_kind: str,
    parameter_name: str,
    variable_name_output: str
) -> List[DeclsVariable]:
    """Get declarations for nested arrays.
    
    Args:
        map_of_properties: Properties schema dictionary
        variable_path: Path to variable
        var_kind: Variable kind
        parameter_name: Parameter name
        variable_name_output: Output variable name
        
    Returns:
        List of DeclsVariables for nested array
    """
    res = []
    
    if not map_of_properties or 'properties' not in map_of_properties:
        return res
    
    properties = map_of_properties['properties']
    if parameter_name not in properties:
        return res
    
    array_schema = properties[parameter_name]
    
    items_datatype = None
    if 'items' in array_schema and isinstance(array_schema['items'], dict):
        items_datatype = array_schema['items'].get('type')
    
    if items_datatype is None:
        items_datatype = 'string'
    
    if (items_datatype.lower() == OBJECT_TYPE_NAME or 
        items_datatype.lower() == ARRAY_TYPE_NAME):
        # Content is object or array type
        decls_vars = get_decls_variables_array(
            variable_path,
            parameter_name,
            parameter_name,
            HASHCODE_TYPE_NAME
        )
        res.extend(decls_vars)
    
    else:
        # Content is primitive type
        translated_datatype = translate_datatype(items_datatype)
        decls_vars = get_decls_variables_array(
            variable_path,
            parameter_name,
            translated_datatype,
            translated_datatype
        )
        res.extend(decls_vars)
    
    return res
