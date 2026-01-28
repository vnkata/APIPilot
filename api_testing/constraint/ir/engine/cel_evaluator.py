"""
CEL (Common Expression Language) evaluator for conditional constraints.

Evaluates CEL expressions to determine if constraints should be applied.
"""

from typing import Any, Dict
import re

from api_testing.constraint.ir.core import ConditionModel
from common.logger import get_logger

logger = get_logger(__name__)


class CELEvaluator:
    """CEL expression evaluator for constraint conditions.

    Simplified CEL evaluator supporting common operations:
    - Comparisons: ==, !=, <, <=, >, >=
    - Logical: &&, ||, !
    - Member access: response.status, request.path.id
    - Literals: integers, strings, booleans

    Note: This is a simplified implementation. For production,
    consider using a full CEL library like celpy.
    """

    def __init__(self):
        """Initialize CEL evaluator."""
        pass

    def evaluate(
        self,
        condition: ConditionModel,
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate condition expression.

        Args:
            condition: ConditionModel with expression
            context: Evaluation context (request, response, etc.)

        Returns:
            True if condition is met, False otherwise
        """
        if condition.lang == "cel":
            return self._evaluate_cel(condition.expr, context)
        elif condition.lang == "python":
            return self._evaluate_python(condition.expr, context)
        else:
            logger.warning(f"Unknown condition language: {condition.lang}")
            return True  # Default to applying constraint

    @staticmethod
    def _evaluate_cel(expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate CEL expression (simplified).

        Args:
            expr: CEL expression
            context: Context dictionary

        Returns:
            Boolean result
        """
        try:
            # Simple CEL expressions we support:
            # - response.status == 200
            # - request.path.id != null
            # - response.status >= 200 && response.status < 300

            # Replace context variables
            expr_eval = expr

            # Replace response.status
            if "response.status" in expr_eval:
                status = context.get("response", {}).get("status", 0)
                expr_eval = expr_eval.replace("response.status", str(status))

            # Replace request references (simplified)
            if "request." in expr_eval:
                # Extract request.path.param pattern
                request_pattern = r"request\.(path|query|header)\.(\w+)"
                matches = re.findall(request_pattern, expr_eval)
                for location, param in matches:
                    value = context.get("request", {}).get(location, {}).get(param)
                    if value is not None:
                        if isinstance(value, str):
                            expr_eval = expr_eval.replace(
                                f"request.{location}.{param}", f"'{value}'"
                            )
                        else:
                            expr_eval = expr_eval.replace(
                                f"request.{location}.{param}", str(value)
                            )

            # Replace logical operators
            expr_eval = expr_eval.replace("&&", " and ")
            expr_eval = expr_eval.replace("||", " or ")

            # Replace null
            expr_eval = expr_eval.replace("null", "None")

            # Evaluate using Python eval (restricted)
            # This is safe because we've replaced all variables
            result = eval(expr_eval, {"__builtins__": {}}, {})

            return bool(result)

        except Exception as e:
            logger.error(
                "Error evaluating CEL expression",
                expr=expr,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Default to True (apply constraint) on error
            return True

    @staticmethod
    def _evaluate_python(expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate Python expression (restricted).

        Args:
            expr: Python expression
            context: Context dictionary

        Returns:
            Boolean result
        """
        try:
            # Evaluate with restricted globals
            result = eval(
                expr,
                {"__builtins__": {}},
                {
                    "response": context.get("response", {}),
                    "request": context.get("request", {}),
                    "context": context,
                },
            )
            return bool(result)

        except Exception as e:
            logger.error(
                "Error evaluating Python expression",
                expr=expr,
                error=str(e),
            )
            return True


__all__ = ["CELEvaluator"]
