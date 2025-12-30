"""
Pydantic models for Constraint IR and validation results.

Defines the data structures for:
- Constraint IR (PredicateModel, CheckModel, OperationConstraintModel, ConstraintIRModel)
- Validation results (Violation, ValidationContext)
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict
from dataclasses import dataclass


class PredicateModel(BaseModel):
    """Single validation predicate.

    Represents a single constraint check (e.g., int.range@v1 with min/max args).
    """

    model_config = ConfigDict(frozen=False)

    kind: str = Field(..., description="Validator kind (e.g., 'int.range')")
    version: str = Field(..., pattern=r"^v\d+$", description="Validator version")
    args: Dict[str, Any] = Field(
        default_factory=dict, description="Validator arguments"
    )


class CheckModel(BaseModel):
    """Single validation check.

    Combines a JSONPath selector with one or more predicates to validate.
    """

    model_config = ConfigDict(frozen=False)

    id: str = Field(..., description="Unique check ID")
    selector: str = Field(
        ..., description="JSONPath selector (e.g., '$.holidays[*].id')"
    )
    predicates: List[PredicateModel] = Field(
        min_length=1, description="List of predicates to apply"
    )
    severity: Literal["error", "warn", "info"] = Field(
        default="error", description="Violation severity"
    )


class OperationConstraintModel(BaseModel):
    """Constraints for a single API operation.

    Contains all validation checks for one operation (e.g., GET /api/v1/holidays).
    """

    model_config = ConfigDict(frozen=False)

    checks: List[CheckModel] = Field(
        default_factory=list, description="List of validation checks"
    )


class ConstraintIRModel(BaseModel):
    """Complete Constraint IR document.

    Top-level model containing all operation constraints for an API specification.
    """

    model_config = ConfigDict(frozen=False)

    version: str = Field(default="v1", description="IR schema version")
    operation_constraints: Dict[str, OperationConstraintModel] = Field(
        ..., description="Map of operation UUID to constraints"
    )


@dataclass
class Violation:
    """Validation violation result.

    Represents a single constraint violation found during validation.
    """

    kind: str  # Validator kind@version (e.g., 'int.range@v1')
    message: str  # Human-readable error message
    path: str  # JSONPath to violated field
    value: Any  # Actual value that violated constraint
    op_key: str  # Operation UUID
    severity: str = "error"  # Violation severity

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "kind": self.kind,
            "message": self.message,
            "path": self.path,
            "value": self.value,
            "op_key": self.op_key,
            "severity": self.severity,
        }


@dataclass
class ValidationContext:
    """Context information for validation execution.

    Provides context to validators during execution.
    """

    op_key: str  # Operation UUID
    path: str  # Current JSONPath being validated
    status_code: Optional[int] = None  # HTTP status code (for response validation)


__all__ = [
    "PredicateModel",
    "CheckModel",
    "OperationConstraintModel",
    "ConstraintIRModel",
    "Violation",
    "ValidationContext",
]
