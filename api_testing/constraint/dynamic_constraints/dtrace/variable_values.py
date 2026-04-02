"""Variable values handling for dtrace generation.

Functions for extracting primitive values and arrays from JSON hierarchies.
Used for both input (enter) and output (exit) values.

Author: Juan C. Alonso (Java), converted to Python
"""

from typing import Any, List, Dict, Optional


def get_primitive_value_from_hierarchy(json_obj: Dict, hierarchy: List[str]) -> Optional[str]:
    """Recursively extract a primitive value from a JSON object following the given hierarchy.
    
    Args:
        json_obj: JSON object to search in
        hierarchy: List of keys to traverse (e.g., ["user", "name"])
        
    Returns:
        String representation of the primitive value, or None if not found
    """
    if not hierarchy or not json_obj:
        return None
    
    from agora.beet.variable.variable_utils import decode_variable_name
    
    key = decode_variable_name(hierarchy[0])
    
    if len(hierarchy) == 1:
        if key not in json_obj or json_obj[key] is None:
            return None
        return str(json_obj[key])
    else:
        json_son = json_obj.get(key)
        
        if isinstance(json_son, dict):  # If nested JSONObject
            return get_primitive_value_from_hierarchy(json_son, hierarchy[1:])
        elif isinstance(json_son, list):  # If JSONArray
            # TODO: Complete for array handling
            return None
    
    return None


def get_array_from_hierarchy(json_obj: Dict, hierarchy: List[str]) -> Optional[List[Any]]:
    """Recursively extract an array from a JSON object following the given hierarchy.
    
    Args:
        json_obj: JSON object to search in
        hierarchy: List of keys to traverse
        
    Returns:
        Array/list if found, None otherwise
    """
    if not hierarchy or not json_obj:
        return None
    
    from agora.beet.variable.variable_utils import decode_variable_name
    
    key = decode_variable_name(hierarchy[0])
    
    if len(hierarchy) == 1:
        return json_obj.get(key)
    else:
        json_son = json_obj.get(key)
        
        if isinstance(json_son, dict):  # If nested JSONObject
            return get_array_from_hierarchy(json_son, hierarchy[1:])
        elif isinstance(json_son, list):  # If JSONArray
            # TODO: Complete for array handling
            return None
    
    return None
