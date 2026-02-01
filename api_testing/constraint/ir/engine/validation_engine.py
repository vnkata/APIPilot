"""
Validation engine for Constraint IR v2.

Executes constraints against API responses using the full IR architecture:
- Scope-aware validation
- JSONPath and request/response selectors
- CEL conditional constraints
- Provenance tracking
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from api_testing.constraint.ir.core import (
    ConstraintIRModel,
    ConstraintModel,
    IRSchemaValidator,
    ValidationResultModel,
    ViolationModel,
)
from api_testing.constraint.ir.engine.cel_evaluator import CELEvaluator
from api_testing.constraint.ir.engine.selectors import SelectorEngine
from api_testing.constraint.ir.primitives import get_validator
from common.logger import get_logger

logger = get_logger(__name__)


class ValidationEngine:
    """Execute constraint validations for IR v2.

    Supports:
    - Multiple selector types (JSONPath, request_ref, response_ref)
    - Conditional constraints (CEL expressions)
    - Multi-predicate constraints
    - Provenance tracking

    Example:
        >>> engine = ValidationEngine(Path(".cache/My API/constraint_ir.json"))
        >>> result = engine.validate_response(
        ...     operation_id="get-/api/v1/holidays",
        ...     response_body={"holidays": [{"id": 1}]},
        ... )
        >>> print(f"Violations: {len(result.violations)}")
    """

    def __init__(self, ir_path: Path):
        """Initialize validation engine.

        Args:
            ir_path: Path to constraint_ir.json file

        Raises:
            FileNotFoundError: If IR file doesn't exist
            ValueError: If IR is invalid
        """
        self.ir_path = ir_path
        self.selector_engine = SelectorEngine()
        self.cel_evaluator = CELEvaluator()

        # Load IR
        logger.info(f"Loading Constraint IR v2 from {ir_path}")

        if not ir_path.exists():
            raise FileNotFoundError(f"Constraint IR not found: {ir_path}")

        with open(ir_path, encoding="utf-8") as f:
            ir_dict = json.load(f)

        # Validate IR
        validator = IRSchemaValidator(schema_version=ir_dict.get("version", "v2"))
        validator.validate_strict(ir_dict)

        # Parse into model
        self.ir = ConstraintIRModel(**ir_dict)

        logger.info(
            "ValidationEngine initialized",
            operations_count=len(self.ir.operation_constraints),
            total_constraints=sum(
                len(oc.constraints) for oc in self.ir.operation_constraints.values()
            ),
        )

    def validate_response(
        self,
        operation_id: str,
        response_body: Any,
        status_code: int = 200,
        request_ctx: dict | None = None,
        response_ctx: dict | None = None,
    ) -> ValidationResultModel:
        """Validate response against constraints.

        Args:
            operation_id: Operation identifier
            response_body: Response data
            status_code: HTTP status code
            request_ctx: Request context (for request_ref selectors)
            response_ctx: Response context (for response_ref selectors)

        Returns:
            ValidationResultModel with results
        """
        # Get constraints for operation
        op_constraints = self.ir.operation_constraints.get(operation_id)
        if not op_constraints:
            logger.debug("No constraints for operation", operation_id=operation_id)
            return ValidationResultModel(
                operation_id=operation_id,
                violations=[],
                constraints_evaluated=0,
                passed=0,
                failed=0,
                skipped=0,
            )

        # Prepare context
        if response_ctx is None:
            response_ctx = {"body": response_body, "status": status_code}
        if request_ctx is None:
            request_ctx = {}

        eval_context = {
            "response": response_ctx,
            "request": request_ctx,
        }

        # Execute constraints
        violations = []
        evaluated = 0
        passed = 0
        failed = 0
        skipped = 0

        for constraint in op_constraints.constraints:
            try:
                # Check condition (if present)
                if constraint.when:
                    if not self.cel_evaluator.evaluate(constraint.when, eval_context):
                        skipped += 1
                        logger.debug(
                            "Skipping constraint (condition not met)",
                            constraint_id=constraint.id,
                            condition=constraint.when.expr,
                        )
                        continue

                evaluated += 1

                # Execute constraint
                constraint_violations = self._execute_constraint(
                    constraint, response_body, request_ctx, response_ctx
                )

                if constraint_violations:
                    violations.extend(constraint_violations)
                    failed += 1
                else:
                    passed += 1

            except Exception as e:
                logger.error(
                    "Error executing constraint",
                    constraint_id=constraint.id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # Create violation for execution error
                violations.append(
                    ViolationModel(
                        constraint_id=constraint.id,
                        predicate_ref="error",
                        message=f"Constraint execution error: {str(e)}",
                        path="",
                        value=None,
                    )
                )
                failed += 1
                evaluated += 1

        result = ValidationResultModel(
            operation_id=operation_id,
            violations=violations,
            constraints_evaluated=evaluated,
            passed=passed,
            failed=failed,
            skipped=skipped,
        )

        logger.info(
            "Validation completed",
            operation_id=operation_id,
            evaluated=evaluated,
            passed=passed,
            failed=failed,
            skipped=skipped,
        )

        return result

    def _execute_constraint(
        self,
        constraint: ConstraintModel,
        response_body: Any,
        request_ctx: dict,
        response_ctx: dict,
    ) -> list[ViolationModel]:
        """Execute a single constraint.

        Args:
            constraint: ConstraintModel to execute
            response_body: Response body
            request_ctx: Request context
            response_ctx: Response context

        Returns:
            List of violations
        """
        violations = []

        # Extract values using selectors
        all_matches = []
        for selector in constraint.selectors:
            matches = self.selector_engine.select(
                selector,
                response_body=response_body,
                request_ctx=request_ctx,
                response_ctx=response_ctx,
            )
            all_matches.append(matches)

        # For cross-field constraints, we need to zip matches
        # For now, handle single selector (most common)
        if len(constraint.selectors) == 1:
            matches = all_matches[0]

            if not matches:
                logger.debug(
                    "No matches for selector",
                    constraint_id=constraint.id,
                    selector=constraint.selectors[0].expr,
                )
                return []

            # Extract values
            values = [m.value for m in matches]

            # Apply each predicate
            for predicate in constraint.predicates:
                predicate_ref = f"{predicate.kind}@{predicate.version}"

                # Get validator function
                validator_fn = get_validator(predicate_ref)
                if not validator_fn:
                    violations.append(
                        ViolationModel(
                            constraint_id=constraint.id,
                            predicate_ref=predicate_ref,
                            message=f"Validator not found: {predicate_ref}",
                            path="",
                            value=None,
                        )
                    )
                    continue

                # Execute validator for each match
                for match in matches:
                    ctx = {
                        "constraint_id": constraint.id,
                        "path": match.path,
                    }

                    pred_violations = validator_fn([match.value], predicate.args, ctx)

                    # Apply severity from constraint
                    for v in pred_violations:
                        v.severity = constraint.severity

                    violations.extend(pred_violations)

        else:
            # Cross-field validation (TODO: implement proper cross-field logic)
            logger.warning(
                "Cross-field constraints not yet fully implemented",
                constraint_id=constraint.id,
            )

        return violations


__all__ = ["ValidationEngine"]
