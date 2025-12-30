"""
JSONPath selector implementation for extracting values from response data.

Uses jsonpath-ng library to parse and execute JSONPath selectors.
Provides caching for compiled selectors to improve performance.
"""

from typing import Any, List, Dict, Set
from dataclasses import dataclass
from jsonpath_ng import parse
from jsonpath_ng.exceptions import JsonPathParserError
from functools import lru_cache
from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SelectorMatch:
    """Single matched value from selector.

    Attributes:
        path: JSONPath to matched value (e.g., 'holidays[0].id')
        value: Actual value at that path
    """

    path: str
    value: Any


@lru_cache(maxsize=1000)
def compile_selector(selector: str):
    """Compile JSONPath selector with caching.

    Compiles JSONPath expressions and caches results for performance.
    The cache size of 1000 should be sufficient for most API specs.

    Args:
        selector: JSONPath selector string (e.g., '$.holidays[*].id')

    Returns:
        Compiled JSONPath expression

    Raises:
        ValueError: If selector syntax is invalid
    """
    try:
        return parse(selector)
    except JsonPathParserError as e:
        logger.error(f"Invalid JSONPath selector", selector=selector, error=str(e))
        raise ValueError(f"Invalid JSONPath selector '{selector}': {e}") from e


def select_values(data: Any, selector: str) -> List[SelectorMatch]:
    """Extract values from data using JSONPath selector.

    Args:
        data: Response data (dict, list, or primitive)
        selector: JSONPath selector (e.g., '$.holidays[*].id')

    Returns:
        List of matched values with their paths

    Example:
        >>> data = {"holidays": [{"id": 1}, {"id": 2}]}
        >>> matches = select_values(data, "$.holidays[*].id")
        >>> [(m.path, m.value) for m in matches]
        [('holidays[0].id', 1), ('holidays[1].id', 2)]
    """
    if data is None:
        logger.debug("Selector received None data")
        return []

    try:
        compiled = compile_selector(selector)
        matches = []

        for match in compiled.find(data):
            # Convert JSONPath match object to our SelectorMatch
            matches.append(SelectorMatch(path=str(match.full_path), value=match.value))

        logger.debug(
            f"Selector matched values",
            selector=selector,
            match_count=len(matches),
        )

        return matches

    except Exception as e:
        logger.error(
            f"Error executing selector",
            selector=selector,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


def dot_notation_to_jsonpath(dot_path: str) -> str:
    """Convert dot notation to JSONPath selector.

    Converts simple dot notation (used in legacy constraints) to JSONPath.
    This maintains backward compatibility while standardizing on JSONPath.

    Args:
        dot_path: Dot notation path (e.g., 'holidays[].id')

    Returns:
        JSONPath selector (e.g., '$.holidays[*].id')

    Example:
        >>> dot_notation_to_jsonpath('holidays[].id')
        '$.holidays[*].id'
        >>> dot_notation_to_jsonpath('user.profile.email')
        '$.user.profile.email'
    """
    # Start with root
    if not dot_path.startswith("$"):
        jsonpath = "$." + dot_path
    else:
        jsonpath = dot_path

    # Convert [] to [*]
    jsonpath = jsonpath.replace("[]", "[*]")

    # Clean up any double dots
    jsonpath = jsonpath.replace("..", ".")

    return jsonpath


def detect_array_paths_from_schema(
    schema_dict: Dict[str, Any], parent_path: str = ""
) -> Set[str]:
    """Recursively traverse schema to identify paths that are arrays.

    This function analyzes the OpenAPI schema structure to determine which
    fields are arrays, enabling correct JSONPath generation with [*] notation.

    Args:
        schema_dict: OpenAPI schema dictionary
        parent_path: Current path being traversed (used in recursion)

    Returns:
        Set of paths like {"holidays", "holidays.provinces", "province.holidays"}

    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "holidays": {
        ...             "type": "array",
        ...             "items": {
        ...                 "type": "object",
        ...                 "properties": {
        ...                     "id": {"type": "integer"},
        ...                     "provinces": {
        ...                         "type": "array",
        ...                         "items": {"type": "object", "properties": {"id": {"type": "integer"}}}
        ...                     }
        ...                 }
        ...             }
        ...         }
        ...     }
        ... }
        >>> detect_array_paths_from_schema(schema)
        {'holidays', 'holidays.provinces'}
    """
    array_paths = set()

    # Guard against None or non-dict inputs
    if not schema_dict or not isinstance(schema_dict, dict):
        return array_paths

    if schema_dict.get("type") == "array":
        if parent_path:
            array_paths.add(parent_path)
        items = schema_dict.get("items", {})
        # Guard against None items
        if items and isinstance(items, dict):
            if items.get("type") == "object" and "properties" in items:
                # Recursively process array items
                array_paths.update(detect_array_paths_from_schema(items, parent_path))

    if schema_dict.get("type") == "object" and "properties" in schema_dict:
        properties = schema_dict.get("properties", {})
        # Guard against None properties
        if properties and isinstance(properties, dict):
            for key, value in properties.items():
                # Guard against None value
                if value is not None:
                    new_path = f"{parent_path}.{key}" if parent_path else key
                    array_paths.update(detect_array_paths_from_schema(value, new_path))

    return array_paths


def is_array_field(field_path: str, array_paths: Set[str]) -> bool:
    """Check if field_path has an array parent in its path.

    Args:
        field_path: Dot notation path (e.g., 'holidays.provinces.id')
        array_paths: Set of paths known to be arrays

    Returns:
        True if any parent segment is an array

    Example:
        >>> array_paths = {'holidays', 'holidays.provinces'}
        >>> is_array_field('holidays.provinces.id', array_paths)
        True
        >>> is_array_field('metadata.version', array_paths)
        False
    """
    parts = field_path.split(".")
    for i in range(len(parts)):
        parent = ".".join(parts[: i + 1])
        if parent in array_paths:
            return True
    return False


def convert_to_jsonpath_with_arrays(field_path: str, array_paths: Set[str]) -> str:
    """Convert dot notation to JSONPath, inserting [*] for array segments.

    This function generates correct JSONPath selectors by analyzing which
    segments in the path are arrays and inserting [*] notation accordingly.

    Args:
        field_path: Dot notation path (e.g., 'holidays.provinces.id')
        array_paths: Set of paths known to be arrays

    Returns:
        JSONPath selector with [*] for array segments

    Example:
        >>> array_paths = {'holidays', 'holidays.provinces'}
        >>> convert_to_jsonpath_with_arrays('holidays.provinces.id', array_paths)
        '$.holidays[*].provinces[*].id'
        >>> convert_to_jsonpath_with_arrays('holidays.id', {'holidays'})
        '$.holidays[*].id'
        >>> convert_to_jsonpath_with_arrays('metadata.version', {'holidays'})
        '$.metadata.version'
    """
    parts = field_path.split(".")
    result_parts = []

    for i, part in enumerate(parts):
        current_path = ".".join(parts[: i + 1])
        result_parts.append(part)
        if current_path in array_paths:
            result_parts.append("[*]")

    # Build final JSONPath, handling [*] placement
    jsonpath = "$"
    for part in result_parts:
        if part == "[*]":
            jsonpath += part
        else:
            jsonpath += "." + part

    # Clean up any edge cases like .[*].
    jsonpath = jsonpath.replace(".[*].", "[*].")

    return jsonpath


__all__ = [
    "SelectorMatch",
    "select_values",
    "compile_selector",
    "dot_notation_to_jsonpath",
    "detect_array_paths_from_schema",
    "is_array_field",
    "convert_to_jsonpath_with_arrays",
]
