from enum import Enum


class FuzzStrategy(Enum):
    BOUNDARY = "boundary"
    INJECTION = "injection"
    ENCODING = "encoding"
    TYPE_ERROR = "type_error"
    OVERFLOW = "overflow"
    CORRUPT = "corrupt"
    EMPTY = "empty"
    LARGE = "large"
    WRONG_TYPE = "wrong_type"
    JUNK = "junk"
    LOGIC_ERROR = "logic_error"
    FORMAT_ERROR = "format_error"
    MUTATE = "mutate"
    OUT_OF_BOUNDS = "out_of_bounds"
    STRUCTURE = "structure"