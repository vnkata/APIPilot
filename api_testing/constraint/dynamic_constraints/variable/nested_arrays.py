"""Nested arrays handling for Beet.

Generates DeclsVariable declarations for nested array properties in schemas.

Author: Juan C. Alonso (Java), converted to Python
"""

from typing import List, Dict, Union, Any, Optional

from api_testing.constraint.dynamic_constraints.decls_variable import DeclsVariable
from api_testing.constraint.dynamic_constraints.variable.variable_utils import (
    translate_datatype, OBJECT_TYPE_NAME, ARRAY_TYPE_NAME, HASHCODE_TYPE_NAME
)
from api_testing.constraint.dynamic_constraints.variable.array_variables import get_decls_variables_array


def get_decls_variables_of_nested_array(
    map_of_properties: Union[Dict, Any],
    variable_path: str,
    var_kind: str,
    parameter_name: str,
    variable_name_output: str
) -> List[DeclsVariable]:
    """Get declarations for nested arrays.
    
    Extracts array properties from a schema and generates corresponding
    DeclsVariable declarations based on the array item type.
    
    Args:
        map_of_properties: Properties schema (dict or ItemProperties object)
        variable_path: Path to variable
        var_kind: Variable kind (e.g., "field")
        parameter_name: Name of the array parameter
        variable_name_output: Output variable name
        
    Returns:
        List of DeclsVariables for nested array
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
    
    if not properties:
        return res
    
    # Check if parameter_name exists in properties
    array_schema = None
    
    if isinstance(properties, dict):
        array_schema = properties.get(parameter_name)
    
    if array_schema is None:
        return res
    
    # Get the items datatype from array_schema
    items_datatype: Optional[str] = None
    
    # Try to get items attribute (for ItemProperties objects)
    if hasattr(array_schema, 'items'):
        items_obj = getattr(array_schema, 'items', None)
        if items_obj is not None:
            if hasattr(items_obj, 'type'):
                items_datatype = getattr(items_obj, 'type', None)
            elif isinstance(items_obj, dict):
                items_datatype = items_obj.get('type')
    
    # Try to get items from dict (for dict objects)
    if items_datatype is None and isinstance(array_schema, dict):
        items_obj = array_schema.get('items')
        if items_obj is not None and isinstance(items_obj, dict):
            items_datatype = items_obj.get('type')
    
    # Default to string if no type found
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
