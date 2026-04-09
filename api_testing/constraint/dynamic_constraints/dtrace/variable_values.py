

from typing import Any, List, Dict, Optional

from api_testing.constraint.dynamic_constraints.variable.variable_utils import decode_variable_name


def get_primitive_value_from_hierarchy(json_obj: Dict[str, Any], hierarchy: List[str]) -> Optional[str]:
    """Recursively extract a primitive value from a JSON object following the given hierarchy.
    
    Args:
        json_obj: JSON object to search in
        hierarchy: List of keys to traverse (e.g., ["user", "name"])
        
    Returns:
        String representation of the primitive value, or None if not found
    """
    if not hierarchy or not isinstance(json_obj, dict):
        return None
    
    key = decode_variable_name(hierarchy[0])
    
    if len(hierarchy) == 1:
        if key not in json_obj or json_obj[key] is None:
            return None
        value = json_obj[key]
        # Convert to string if not already
        return value
    else:
        json_son = json_obj.get(key)
        
        if isinstance(json_son, dict):  # If nested JSONObject
            return get_primitive_value_from_hierarchy(json_son, hierarchy[1:])
        elif isinstance(json_son, list):  # If JSONArray
            # For arrays, we might want to get the first element or handle differently
            # For now, return None as arrays are handled separately
            return None
    
    return None


def get_array_from_hierarchy(json_obj: Dict[str, Any], hierarchy: List[str]) -> Optional[List[Any]]:
    """Recursively extract an array from a JSON object following the given hierarchy.
    
    Args:
        json_obj: JSON object to search in
        hierarchy: List of keys to traverse
        
    Returns:
        Array/list if found, None otherwise
    """
    if not hierarchy or not isinstance(json_obj, dict):
        return None
    
    key = decode_variable_name(hierarchy[0])
    
    if len(hierarchy) == 1:
        value = json_obj.get(key)
        return value if isinstance(value, list) else None
    else:
        json_son = json_obj.get(key)
        
        if isinstance(json_son, dict):  # If nested JSONObject
            return get_array_from_hierarchy(json_son, hierarchy[1:])
        elif isinstance(json_son, list):  # If JSONArray at intermediate level
            # This is complex - for now, return None
            # Could be enhanced to handle array indexing like array[0].field
            return None
    
    return None
