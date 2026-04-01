"""Variable utility module for Beet."""

# Global constants
HIERARCHY_SEPARATOR = "&"
ARRAY_NESTING_SEPARATOR = "%"

# Type names
HASHCODE_TYPE_NAME = "hashcode"
STRING_TYPE_NAME = "string"
DOUBLE_TYPE_NAME = "double"
INTEGER_TYPE_NAME = "int"
BOOLEAN_TYPE_NAME = "boolean"
OBJECT_TYPE_NAME = "object"
ARRAY_TYPE_NAME = "array"

PRIMITIVE_TYPES = [STRING_TYPE_NAME, DOUBLE_TYPE_NAME, INTEGER_TYPE_NAME, BOOLEAN_TYPE_NAME]


def translate_datatype(input_type: str) -> str:
    """Convert OpenAPI datatype to Daikon datatype.
    
    Args:
        input_type: OpenAPI type name
        
    Returns:
        Daikon type name
    """
    if input_type is None:
        return STRING_TYPE_NAME
    
    input_lower = input_type.lower()
    
    if input_lower == "number":
        return DOUBLE_TYPE_NAME
    elif input_lower == "integer":
        return INTEGER_TYPE_NAME
    elif input_lower == "boolean":
        return BOOLEAN_TYPE_NAME
    elif input_lower == "object":
        return OBJECT_TYPE_NAME
    elif input_lower == "array":
        return ARRAY_TYPE_NAME
    else:
        return STRING_TYPE_NAME


def encode_variable_name(variable_name: str) -> str:
    """Encode variable name by replacing special characters.
    
    Args:
        variable_name: Variable name to encode
        
    Returns:
        Encoded variable name
    """
    return variable_name.replace(".", HIERARCHY_SEPARATOR)


def decode_variable_name(encoded_variable_name: str) -> str:
    """Decode variable name by replacing back special characters.
    
    Args:
        encoded_variable_name: Encoded variable name
        
    Returns:
        Decoded variable name
    """
    return encoded_variable_name.replace(HIERARCHY_SEPARATOR, ".")
