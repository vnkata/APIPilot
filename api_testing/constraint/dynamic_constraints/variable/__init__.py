"""Variable module for Beet."""
from .enter_variables import get_list_of_decls_variables, get_decls_variables_of_body_parameters
from .exit_variables import generate_decls_variables_of_exit
from .array_variables import generate_decls_variables_of_array, generate_decls_variables_of_array_exit  
from .nested_arrays import get_decls_variables_of_nested_array
from .variable_utils import HIERARCHY_SEPARATOR, HASHCODE_TYPE_NAME, translate_datatype, PRIMITIVE_TYPES, ARRAY_TYPE_NAME

__all__ = ["EnterVariables"]
