"""Array variables handling for Beet."""

from typing import List
from agora.beet.model.decls_variable import DeclsVariable
from agora.beet.variable.variable_utils import (
    encode_variable_name, translate_datatype,
    PRIMITIVE_TYPES, ARRAY_TYPE_NAME, HASHCODE_TYPE_NAME
)


def generate_decls_variables_of_array(
    array_schema: Dict,
    variable_path: str,
    variable_name: str,
    var_kind: str,
    enclosing_var: str,
    dectype: str
) -> DeclsVariable:
    """Generate declarations for array variables.
    
    Args:
        array_schema: Array schema dictionary
        variable_path: Path to variable
        variable_name: Variable name
        var_kind: Variable kind
        enclosing_var: Enclosing variable name
        dectype: Declaration type
        
    Returns:
        DeclsVariable for array
    """
    res = generate_decls_variables_of_array_exit(
        array_schema,
        dectype,
        variable_name,
        var_kind,
        variable_path
    )
    res.enclosing_var = enclosing_var
    return res


def generate_decls_variables_of_array_exit(
    array_schema: Dict,
    dec_type: str,
    variable_name: str,
    var_kind: str,
    variable_path: str
) -> DeclsVariable:
    """Generate declarations for array exit variables.
    
    Args:
        array_schema: Array schema dictionary
        dec_type: Declaration type
        variable_name: Variable name
        var_kind: Variable kind
        variable_path: Path to variable
        
    Returns:
        DeclsVariable for array exit
    """
    father = DeclsVariable(
        variable_name,
        variable_path,
        var_kind,
        dec_type,
        HASHCODE_TYPE_NAME,
        None
    )
    
    items_datatype = None
    if isinstance(array_schema, dict) and 'items' in array_schema:
        items_datatype = array_schema['items'].get('type')
    
    if items_datatype is None:
        items_datatype = 'string'
    
    translated_datatype = translate_datatype(items_datatype)
    
    updated_variable_path = encode_variable_name(variable_name)
    if variable_path:
        updated_variable_path = f"{variable_path}.{encode_variable_name(variable_name)}"
    
    if translated_datatype in PRIMITIVE_TYPES:
        enclosed_vars = get_decls_variables_array(
            updated_variable_path,
            ARRAY_TYPE_NAME,
            translated_datatype,
            translated_datatype
        )
    else:
        enclosed_vars = get_decls_variables_array(
            updated_variable_path,
            ARRAY_TYPE_NAME,
            ARRAY_TYPE_NAME,
            HASHCODE_TYPE_NAME
        )
    
    father.enclosed_variables = enclosed_vars
    return father


def get_decls_variables_array(
    variable_path: str,
    parameter_name: str,
    dec_type: str,
    rep_type: str
) -> List[DeclsVariable]:
    """Get declarations for array elements.
    
    Args:
        variable_path: Path to variable
        parameter_name: Parameter name
        dec_type: Declaration type
        rep_type: Representation type
        
    Returns:
        List of DeclsVariables for array
    """
    res = []
    
    array_indicator = "[]"
    
    if dec_type not in PRIMITIVE_TYPES:
        dec_type = encode_variable_name(dec_type)
    
    # Add array field variable
    field_var = DeclsVariable(
        parameter_name,
        variable_path,
        f"field {parameter_name}",
        f"{dec_type}{array_indicator}",
        HASHCODE_TYPE_NAME,
        variable_path
    )
    res.append(field_var)
    
    # Add array elements variable
    array_elements_var = DeclsVariable(
        parameter_name,
        variable_path,
        ARRAY_TYPE_NAME,
        f"{dec_type}{array_indicator}",
        f"{rep_type}{array_indicator}",
        f"{variable_path}.{encode_variable_name(parameter_name)}"
    )
    array_elements_var.variable_name = f"{array_elements_var.variable_name}[..]"
    res.append(array_elements_var)
    
    return res
