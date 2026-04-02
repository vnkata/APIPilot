"""Exit variables handling for Beet."""

from typing import List, Dict, Optional
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
    
    Args:
        variable_name: Name of the variable
        var_kind: Kind of variable
        variable_name_output: Output variable name
        map_of_properties: Properties schema dictionary
        
    Returns:
        Root DeclsVariable with enclosed variables
    """
    father = DeclsVariable(
        variable_name,
        None,
        var_kind,
        variable_name_output,
        HASHCODE_TYPE_NAME,
        None
    )
    
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
    map_of_properties: Dict,
    parent_variable: str,
    var_kind: str,
    variable_name_output: str,
    is_array: bool
) -> List[DeclsVariable]:
    """Recursively generate exit variables.
    
    Args:
        map_of_properties: Properties schema dictionary  
        parent_variable: Parent variable name
        var_kind: Variable kind
        variable_name_output: Output variable name
        is_array: Whether this is an array
        
    Returns:
        List of DeclsVariables
    """
    res = []
    
    if not map_of_properties:
        return res
    
    properties = map_of_properties.get('properties', {})
    
    if not properties:
        return res
    
    for param_name, schema in properties.items():
        param_type = schema.get('type') if isinstance(schema, dict) else None
        
        if param_type is None or param_type.lower() == OBJECT_TYPE_NAME:
            # Object type
            decls_var = DeclsVariable(
                param_name,
                parent_variable,
                f"field {param_name}",
                f"{variable_name_output}{HIERARCHY_SEPARATOR}{encode_variable_name(param_name)}",
                HASHCODE_TYPE_NAME,
                parent_variable,
                is_array
            )
            
            # Recursive call for nested properties
            enclosed = _generate_decls_variables_of_exit_recursive(
                schema,
                f"{parent_variable}.{encode_variable_name(param_name)}",
                var_kind,
                variable_name_output,
                False
            )
            decls_var.enclosed_variables = enclosed
            res.append(decls_var)
        
        elif param_type.lower() == ARRAY_TYPE_NAME:
            # Array type - would need to call nested array handler
            pass
        
        else:
            # Primitive type
            decls_var = DeclsVariable(
                param_name,
                parent_variable,
                f"field {param_name}",
                translate_datatype(param_type),
                translate_datatype(param_type),
                parent_variable,
                is_array
            )
            res.append(decls_var)
    
    return res


def generate_decls_variables_of_primitive_response(
    parameter_type: str,
    object_name: str,
    parent_variable: str,
    var_kind: str
) -> DeclsVariable:
    """Generate declarations for primitive response.
    
    Args:
        parameter_type: Parameter type
        object_name: Object name
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
    
    translated_type = translate_datatype(parameter_type)
    
    enclosed_var = DeclsVariable(
        "primitive",
        parent_variable,
        "field primitive",
        translated_type,
        translated_type,
        parent_variable,
        False
    )
    
    father.enclosed_variables = [enclosed_var]
    return father
