"""
Core primitive validator implementations.

This module imports validators from organized subdirectories for better maintainability.
Each category has its own subdirectory: int/, string/, date/, number/, boolean/, array/,
comparison/, request_response/.
"""

# Import from subdirectories
from api_testing.constraint.ir.primitives.validator.array import (
    array_length_v1,
    array_unique_v1,
)
from api_testing.constraint.ir.primitives.validator.boolean import (
    boolean_const_v1,
)

# Import comparison validators
from api_testing.constraint.ir.primitives.validator.comparison import (
    comparison_between_v1,
    comparison_equals_v1,
    comparison_greater_than_or_equal_v1,
    comparison_greater_than_v1,
    comparison_less_than_or_equal_v1,
    comparison_less_than_v1,
    comparison_not_equals_v1,
)
from api_testing.constraint.ir.primitives.validator.date import (
    date_iso_date_v1,
    date_iso_datetime_v1,
)
from api_testing.constraint.ir.primitives.validator.int import (
    int_enum_v1,
    int_positive_v1,
    int_range_v1,
)
from api_testing.constraint.ir.primitives.validator.number import (
    number_positive_v1,
    number_range_v1,
)

# Import request_response validators
from api_testing.constraint.ir.primitives.validator.request_response import (
    contains_substring_v1,
    date_in_range_v1,
    exists_v1,
    field_absent_v1,
    field_exists_v1,
    forall_eq_v1,
    implies_v1,
    len_eq_v1,
    len_ge_v1,
    len_le_v1,
    sorted_by_v1,
)
from api_testing.constraint.ir.primitives.validator.string import (
    string_email_v1,
    string_enum_v1,
    string_length_v1,
    string_pattern_v1,
    string_uri_v1,
)

# ============================================================================
# Registry
# ============================================================================

VALIDATOR_REGISTRY = {
    # Integer validators
    "int.range@v1": int_range_v1,
    "int.enum@v1": int_enum_v1,
    "int.positive@v1": int_positive_v1,
    # String validators
    "string.enum@v1": string_enum_v1,
    "string.pattern@v1": string_pattern_v1,
    "string.length@v1": string_length_v1,
    "string.uri@v1": string_uri_v1,
    "string.email@v1": string_email_v1,
    # Date validators
    "date.iso_date@v1": date_iso_date_v1,
    "date.iso_datetime@v1": date_iso_datetime_v1,
    # Number validators
    "number.range@v1": number_range_v1,
    "number.positive@v1": number_positive_v1,
    # Boolean validators
    "boolean.const@v1": boolean_const_v1,
    # Array validators
    "array.length@v1": array_length_v1,
    "array.unique@v1": array_unique_v1,
    # Comparison validators
    "comparison.less_than@v1": comparison_less_than_v1,
    "comparison.less_than_or_equal@v1": comparison_less_than_or_equal_v1,
    "comparison.greater_than@v1": comparison_greater_than_v1,
    "comparison.greater_than_or_equal@v1": comparison_greater_than_or_equal_v1,
    "comparison.equals@v1": comparison_equals_v1,
    "comparison.not_equals@v1": comparison_not_equals_v1,
    "comparison.between@v1": comparison_between_v1,
    # Request-response validators
    "forall_eq@v1": forall_eq_v1,
    "exists@v1": exists_v1,
    "len_le@v1": len_le_v1,
    "len_eq@v1": len_eq_v1,
    "len_ge@v1": len_ge_v1,
    "sorted_by@v1": sorted_by_v1,
    "implies@v1": implies_v1,
    "contains_substring@v1": contains_substring_v1,
    "date_in_range@v1": date_in_range_v1,
    "field_exists@v1": field_exists_v1,
    "field_absent@v1": field_absent_v1,
}


def get_validator(predicate_ref: str):
    """Get validator function by reference."""
    return VALIDATOR_REGISTRY.get(predicate_ref)


__all__ = ["VALIDATOR_REGISTRY", "get_validator"]
