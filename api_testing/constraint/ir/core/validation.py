"""
Constraint IR validation - separates valid/invalid/proposed predicates.

Validates constraints against the predicate registry, ensuring that:
- All predicates exist in the registry
- Arguments match the predicate's expected schema
- Proposed predicates are saved for review rather than included in production IR
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from api_testing.constraint.ir.core.models import ConstraintModel, PredicateModel
from api_testing.constraint.ir.primitives.registry_loader import (
    get_predicate,
    validate_predicate_args,
    ProposedPredicateManager,
)
from common.logger import get_logger

logger = get_logger(__name__)


class InvalidConstraint(BaseModel):
    """A constraint that failed validation.

    Attributes:
        constraint: The invalid constraint
        error_message: Why validation failed
        error_type: Type of validation error (missing_predicate, invalid_args, etc.)
    """

    model_config = {"frozen": False}

    constraint: ConstraintModel = Field(..., description="The invalid constraint")
    error_message: str = Field(..., description="Validation error message")
    error_type: str = Field(
        ..., description="Error type: missing_predicate, invalid_args, validation_error"
    )


class ProposedPredicate(BaseModel):
    """A predicate that doesn't exist in registry but was extracted by LLM.

    These are saved for human review rather than included in production IR.

    Attributes:
        kind: Predicate kind (e.g., 'string.is_canadian_province')
        version: Version string
        args: Arguments that would be used
        field_path: Where it was proposed
        evidence: Evidence from spec/description
        proposed_at: ISO timestamp
    """

    model_config = {"frozen": False}

    kind: str = Field(..., description="Proposed predicate kind")
    version: str = Field(default="v1", description="Version")
    args: Dict[str, Any] = Field(default_factory=dict, description="Arguments")
    field_path: str = Field(..., description="Field context")
    evidence: str = Field(..., description="Evidence from specification")
    proposed_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="When proposed",
    )


class ValidationResult(BaseModel):
    """Result of constraint validation.

    Separates constraints into valid (can be used), invalid (errors),
    and proposed (need review).

    Attributes:
        valid_constraints: Constraints that passed validation
        invalid_constraints: Constraints that failed validation
        proposed_predicates: New predicates needing review
        stats: Validation statistics
    """

    model_config = {"frozen": False}

    valid_constraints: List[ConstraintModel] = Field(
        default_factory=list, description="Valid constraints ready for IR"
    )
    invalid_constraints: List[InvalidConstraint] = Field(
        default_factory=list, description="Constraints that failed validation"
    )
    proposed_predicates: List[ProposedPredicate] = Field(
        default_factory=list, description="New predicates needing human review"
    )
    stats: Dict[str, int] = Field(
        default_factory=dict, description="Validation statistics"
    )

    @property
    def total_constraints(self) -> int:
        """Total number of constraints processed."""
        return (
            len(self.valid_constraints)
            + len(self.invalid_constraints)
            + len(self.proposed_predicates)
        )


class ConstraintIRValidator:
    """Validates constraints and separates valid/invalid/proposed.

    Main validation workflow:
    1. Check each predicate exists in registry
    2. Validate args against predicate's schema
    3. Separate into valid/invalid/proposed categories
    4. Save proposed predicates for review
    5. Log invalid constraints but don't fail pipeline

    Example:
        >>> validator = ConstraintIRValidator()
        >>> result = validator.validate_constraints(constraints)
        >>> print(f"Valid: {len(result.valid_constraints)}")
        >>> print(f"Invalid: {len(result.invalid_constraints)}")
        >>> print(f"Proposed: {len(result.proposed_predicates)}")
    """

    def __init__(
        self,
        proposal_manager: Optional[ProposedPredicateManager] = None,
        strict_mode: bool = False,
    ):
        """Initialize validator.

        Args:
            proposal_manager: Manager for saving proposed predicates (optional)
            strict_mode: If True, log warnings for unimplemented predicates
        """
        self.proposal_manager = proposal_manager or ProposedPredicateManager()
        self.strict_mode = strict_mode
        self.logger = logger

    def validate_constraints(
        self, constraints: List[ConstraintModel]
    ) -> ValidationResult:
        """Validate all constraints against registry.

        Args:
            constraints: List of constraints to validate

        Returns:
            ValidationResult with separated valid/invalid/proposed
        """
        valid: List[ConstraintModel] = []
        invalid: List[InvalidConstraint] = []
        proposed: List[ProposedPredicate] = []

        for constraint in constraints:
            # Validate each predicate in the constraint
            for predicate in constraint.predicates:
                validation_status = self._validate_predicate(
                    predicate, constraint.metadata.get("field_path", "unknown")
                )

                if validation_status["status"] == "valid":
                    valid.append(constraint)
                elif validation_status["status"] == "invalid":
                    invalid.append(
                        InvalidConstraint(
                            constraint=constraint,
                            error_message=validation_status["error"],
                            error_type=validation_status["error_type"],
                        )
                    )
                elif validation_status["status"] == "proposed":
                    proposed.append(
                        ProposedPredicate(
                            kind=predicate.kind,
                            version=predicate.version,
                            args=predicate.args,
                            field_path=constraint.metadata.get("field_path", "unknown"),
                            evidence=constraint.source.evidence or "No evidence",
                        )
                    )

        # Save proposed predicates
        if proposed:
            self._save_proposed_predicates(proposed)

        # Log summary
        stats = {
            "valid": len(valid),
            "invalid": len(invalid),
            "proposed": len(proposed),
            "total": len(constraints),
        }

        self.logger.info(
            "Constraint validation complete",
            valid=stats["valid"],
            invalid=stats["invalid"],
            proposed=stats["proposed"],
            total=stats["total"],
        )

        if invalid:
            self.logger.warning(
                f"Found {len(invalid)} invalid constraints (will be excluded from IR)",
                invalid_count=len(invalid),
            )

        if proposed:
            self.logger.info(
                f"Found {len(proposed)} proposed predicates (saved for review)",
                proposed_count=len(proposed),
            )

        return ValidationResult(
            valid_constraints=valid,
            invalid_constraints=invalid,
            proposed_predicates=proposed,
            stats=stats,
        )

    def _validate_predicate(
        self, predicate: PredicateModel, field_path: str
    ) -> Dict[str, Any]:
        """Validate a single predicate.

        Args:
            predicate: Predicate to validate
            field_path: Field context for logging

        Returns:
            Dict with status ("valid", "invalid", "proposed") and optional error info
        """
        # Check if predicate exists in registry
        meta = get_predicate(predicate.kind, predicate.version)

        if not meta:
            # Predicate doesn't exist - it's a proposal
            self.logger.debug(
                "Predicate not in registry (proposed)",
                predicate=f"{predicate.kind}@{predicate.version}",
                field_path=field_path,
            )
            return {
                "status": "proposed",
                "error": f"Predicate {predicate.kind}@{predicate.version} not in registry",
            }

        # Predicate exists - validate args
        if not validate_predicate_args(
            predicate.kind, predicate.version, predicate.args
        ):
            self.logger.error(
                "Predicate args validation failed",
                predicate=f"{predicate.kind}@{predicate.version}",
                args=predicate.args,
                field_path=field_path,
            )
            return {
                "status": "invalid",
                "error": f"Invalid args for {predicate.kind}@{predicate.version}",
                "error_type": "invalid_args",
            }

        # Check if implemented (warning only in strict mode)
        if self.strict_mode and not meta.implemented:
            self.logger.warning(
                "Predicate not implemented yet",
                predicate=f"{predicate.kind}@{predicate.version}",
                field_path=field_path,
            )

        return {"status": "valid"}

    def _save_proposed_predicates(self, proposed: List[ProposedPredicate]) -> None:
        """Save proposed predicates to file for review.

        Args:
            proposed: List of proposed predicates
        """
        if not self.proposal_manager:
            return

        for pred in proposed:
            try:
                success = self.proposal_manager.save_proposed(
                    predicate_kind=pred.kind,
                    args_schema={
                        "type": "object",
                        "properties": {k: {"type": "string"} for k in pred.args.keys()},
                        "additionalProperties": False,
                    },
                    description=f"LLM-proposed predicate for field {pred.field_path}",
                    evidence=pred.evidence,
                    proposed_by="llm",
                    field_context=pred.field_path,
                )

                if success:
                    self.logger.debug(
                        "Saved proposed predicate",
                        predicate=pred.kind,
                        field_path=pred.field_path,
                    )
            except Exception as e:
                self.logger.error(
                    "Failed to save proposed predicate",
                    predicate=pred.kind,
                    error=str(e),
                )


__all__ = [
    "InvalidConstraint",
    "ProposedPredicate",
    "ValidationResult",
    "ConstraintIRValidator",
]
