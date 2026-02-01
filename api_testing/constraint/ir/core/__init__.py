"""
Constraint IR models and schemas.

Defines the complete Constraint IR v2 architecture with:
- Enhanced models with Scope, Provenance, Conditions
- JSONPath and request/response selectors
- CEL conditional expressions
- Comprehensive validation
"""

from api_testing.constraint.ir.core.builder import ConstraintIRBuilder
from api_testing.constraint.ir.core.models import (
    ConditionModel,
    ConstraintIRModel,
    ConstraintModel,
    OperationConstraintsModel,
    PredicateModel,
    ProvenanceModel,
    ScopeModel,
    SelectorModel,
    ValidationResultModel,
    ViolationModel,
)
from api_testing.constraint.ir.core.parameter_model import ParameterInfo
from api_testing.constraint.ir.core.validator import IRSchemaValidator

__all__ = [
    "SelectorModel",
    "ConditionModel",
    "ProvenanceModel",
    "ScopeModel",
    "PredicateModel",
    "ConstraintModel",
    "OperationConstraintsModel",
    "ConstraintIRModel",
    "ViolationModel",
    "ValidationResultModel",
    "IRSchemaValidator",
    "ConstraintIRBuilder",
    "ParameterInfo",
]
