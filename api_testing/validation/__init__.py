"""
Constraint validation system for API responses.

This package provides:
- Validator primitives (int, string, date validators)
- Validation engine with JSONPath selectors
- Constraint IR models and builders
- Pytest plugin integration
"""

from api_testing.validation.models import (
    PredicateModel,
    CheckModel,
    OperationConstraintModel,
    ConstraintIRModel,
    Violation,
    ValidationContext,
)
from api_testing.validation.registry import ValidatorRegistry
from api_testing.validation.engine import ValidationEngine
from api_testing.validation.selectors import select_values, SelectorMatch

__all__ = [
    "PredicateModel",
    "CheckModel",
    "OperationConstraintModel",
    "ConstraintIRModel",
    "Violation",
    "ValidationContext",
    "ValidatorRegistry",
    "ValidationEngine",
    "select_values",
    "SelectorMatch",
]
