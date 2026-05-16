"""Array nesting management utilities for Beet."""

from typing import List, Dict, Any, Union


def do_bubble_sort(json_array: List[Any]) -> List[Dict[str, Any]]:
    """Flatten all objects contained within nested arrays.

    Based on: https://stackoverflow.com/questions/54008740/parse-multi-dimensional-json-array-to-flat-int-list-in-java
    This function flattens all the objects contained within nested arrays.

    Args:
        json_array: JSONArray-like list to flatten

    Returns:
        List of flattened JSONObjects (dictionaries)
    """
    if json_array is None:
        return []

    result = []
    for element in json_array:
        try:
            if element is not None:
                flattened = _get_or_flatten(element)
                result.extend(flattened)
        except Exception as e:
            print(f"Error processing element {element}: {e}")

    return result


def _get_or_flatten(obj: Any) -> List[Dict[str, Any]]:
    """Recursively flatten nested structures to extract all dictionaries.

    Args:
        obj: Object to flatten (dict, list, or other)

    Returns:
        List of dictionaries found in the structure

    Raises:
        Exception: If object type is not supported
    """
    result = []

    if isinstance(obj, dict):
        # If it's a dictionary (JSONObject), add it to result
        result = [obj]
    elif isinstance(obj, list):
        # If it's a list, recursively process each element
        for item in obj:
            try:
                if item is not None:
                    flattened = _get_or_flatten(item)
                    result.extend(flattened)
            except Exception as e:
                print(f"Error processing nested item {item}: {e}")
    else:
        raise Exception(f"{type(obj).__name__} is not supported at _get_or_flatten")

    return result


def get_json_arrays_of_specified_nesting_level(
    json_array: List[Any],
    target_nesting_level: int,
    current_nesting_level: int = 0
) -> List[List[Any]]:
    """Get all arrays that belong to the provided target nesting level.

    Args:
        json_array: The JSONArray to search
        target_nesting_level: The target nesting level to find
        current_nesting_level: Current nesting level (used in recursion)

    Returns:
        List of JSONArrays at the specified nesting level

    Raises:
        ValueError: If target_nesting_level is less than current_nesting_level
    """
    if current_nesting_level > target_nesting_level:
        raise ValueError("target_nesting_level must be greater or equal than current_nesting_level")

    result = []

    if current_nesting_level != target_nesting_level:
        # Case 1: The nesting level IS NOT the target one
        # Recursive call increasing the nesting level
        next_level = current_nesting_level + 1
        if json_array is not None:
            for element in json_array:
                if isinstance(element, list):
                    result.extend(
                        get_json_arrays_of_specified_nesting_level(
                            element, target_nesting_level, next_level
                        )
                    )
    else:
        # Case 2: The nesting level IS the target one
        # Base case: return the json_array
        result.append(json_array)

    return result
