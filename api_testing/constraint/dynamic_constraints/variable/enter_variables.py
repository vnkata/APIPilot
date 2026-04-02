"""Enter variables handling for Beet."""

from typing import List, Optional
from api_testing.constraint.dynamic_constraints.decls_variable import DeclsVariable
from api_testing.constraint.dynamic_constraints.variable.variable_utils import (
    translate_datatype, OBJECT_TYPE_NAME, ARRAY_TYPE_NAME, HASHCODE_TYPE_NAME
)


def get_list_of_decls_variables(object_name: str, root_variable_name: str, operation) -> DeclsVariable:
    """Generate declarations variables for enter program point.
    
    Args:
        object_name: Name of the object
        root_variable_name: Root variable name
        operation: OpenAPI operation object
        
    Returns:
        Root DeclsVariable with enclosed variables
    """
    # Create root variable
    father = DeclsVariable(
        root_variable_name, 
        None, 
        "variable",
        object_name, 
        HASHCODE_TYPE_NAME, 
        None
    )
    
    enclosed_variables = []
    
    # Extract parameters from operation
    if hasattr(operation, 'parameters') and operation.parameters:
        for parameter_name, parameter in operation.parameters.items():
            param_type = parameter.schema.type if hasattr(parameter, 'schema') else None
            if param_type is None:
                raise ValueError(
                    f"Please specify the parameter type for parameter {parameter.get('name', 'unknown')}\n"
                    "If the error persists, specify it explicitly in the 'parameters' field"
                )
            
            if param_type.lower() == OBJECT_TYPE_NAME:
                raise ValueError("Please provide a primitive object or an array as input parameter")
            
            elif param_type.lower() == ARRAY_TYPE_NAME:
                # Handle array parameters
                from .array_variables import get_decls_variables_array
                decls_vars = get_decls_variables_array(
                    root_variable_name,
                    getattr(parameter, 'name', 'unknown'),
                    HASHCODE_TYPE_NAME,
                    HASHCODE_TYPE_NAME
                )
                enclosed_variables.extend(decls_vars)
            
            else:
                # Primitive type parameter
                param_name = parameter_name
                decls_var = DeclsVariable(
                    param_name,
                    root_variable_name,
                    f"field {param_name}",
                    translate_datatype(param_type),
                    translate_datatype(param_type),
                    father.variable_name
                )
                enclosed_variables.append(decls_var)
    
    # Handle request body parameters
    if hasattr(operation, 'requestBody') and operation.requestBody:
        body_vars = get_decls_variables_of_body_parameters(
            operation, root_variable_name, object_name
        )
        enclosed_variables.extend(body_vars)
    
    father.enclosed_variables = enclosed_variables
    return father


def get_decls_variables_of_body_parameters(
    operation, 
    root_variable_name: str, 
    object_name: str
) -> List[DeclsVariable]:
    """Extract variables from request body.
    
    Args:
        operation: OpenAPI operation object
        root_variable_name: Root variable name
        object_name: Object name
        
    Returns:
        List of DeclsVariables from body
    """
    res = []
    # Implementation would depend on OpenAPI operation structure
    # This is a placeholder
    return res
