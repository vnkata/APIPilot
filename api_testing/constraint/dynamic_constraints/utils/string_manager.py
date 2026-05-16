"""String management utilities for Beet."""

import json
from urllib.parse import quote, unquote


def encode_string(parameter_name: str) -> str:
    """Encode URL special characters.
    
    Args:
        parameter_name: Name of parameter to encode
        
    Returns:
        URL-encoded string
        
    Raises:
        ValueError: If parameter is None
    """
    if parameter_name is None:
        raise ValueError("parameter_name cannot be None")
    return quote(parameter_name, safe='')


def decode_string(parameter_value: str) -> str:
    """Decode URL special characters.
    
    Args:
        parameter_value: URL-encoded string
        
    Returns:
        Decoded string
        
    Raises:
        ValueError: If parameter is None
    """
    if parameter_value is None:
        raise ValueError("parameter_value cannot be None")
    if not isinstance(parameter_value, str):
        return parameter_value
    try:
        val = json.loads(parameter_value)
        if isinstance(val, list):
            if len(val) == 1:
                return val[0]
        return val
    except Exception as e:
        return unquote(parameter_value)
