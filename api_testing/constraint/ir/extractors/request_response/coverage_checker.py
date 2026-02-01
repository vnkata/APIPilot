"""
Coverage checker for request-response constraints.

Identifies request parameters that weren't matched by heuristic extractors.
"""

import re

from api_testing.constraint.ir.core.parameter_model import ParameterInfo
from api_testing.constraint.ir.extractors.common import CandidateConstraint
from api_testing.models.specification_model import OperationProperties
from common.logger import get_logger

logger = get_logger(__name__)


class RequestResponseCoverageChecker:
    """Identifies unmatched request parameters.

    Checks which parameters have constraints extracted by heuristics
    and returns those that don't.
    """

    def __init__(self):
        """Initialize coverage checker."""
        self.logger = logger

    def find_unmatched_parameters(
        self,
        operation: OperationProperties,
        extracted_candidates: list[CandidateConstraint],
    ) -> list[ParameterInfo]:
        """Find request parameters not covered by extracted constraints.

        Args:
            operation: Operation properties
            extracted_candidates: Candidates from heuristic extraction

        Returns:
            List of unmatched parameters
        """
        # Get all request parameters
        all_params = []

        try:
            all_params.extend(operation.get_path_parameters())
        except Exception as e:
            self.logger.debug(
                f"Could not get path parameters: {e}",
                operation=operation.uuid,
            )

        try:
            all_params.extend(operation.get_query_parameters())
        except Exception as e:
            self.logger.debug(
                f"Could not get query parameters: {e}",
                operation=operation.uuid,
            )

        try:
            all_params.extend(operation.get_header_parameters())
        except Exception as e:
            self.logger.debug(
                f"Could not get header parameters: {e}",
                operation=operation.uuid,
            )

        if not all_params:
            self.logger.debug(
                "No request parameters found",
                operation=operation.uuid,
            )
            return []

        # Extract covered parameter names from candidates
        covered_params = self._extract_covered_params(extracted_candidates)

        # Find unmatched parameters
        unmatched = []
        for param in all_params:
            # Normalize param name for comparison
            normalized_name = self._normalize_param_name(param.name)

            # Check if this param is covered
            if not any(
                normalized_name == self._normalize_param_name(covered)
                for covered in covered_params
            ):
                unmatched.append(param)

        if unmatched:
            self.logger.info(
                f"Found {len(unmatched)} unmatched parameters out of {len(all_params)}",
                operation=operation.uuid,
                unmatched_names=[p.name for p in unmatched],
            )
        else:
            self.logger.info(
                f"All {len(all_params)} parameters are covered",
                operation=operation.uuid,
            )

        return unmatched

    def _extract_covered_params(
        self,
        candidates: list[CandidateConstraint],
    ) -> set[str]:
        """Extract parameter names from candidate selectors.

        Args:
            candidates: List of candidate constraints

        Returns:
            Set of covered parameter names
        """
        covered = set()

        for candidate in candidates:
            for selector in candidate.selectors:
                # Extract param name from selector
                # Format: $request.query.paramName or $request.path.paramName
                if "$request." in selector:
                    # Extract param name after last dot
                    parts = selector.split(".")
                    if len(parts) >= 3:
                        param_name = parts[-1].rstrip("$")
                        covered.add(param_name)

        return covered

    def _normalize_param_name(self, name: str) -> str:
        """Normalize parameter name for comparison.

        Args:
            name: Parameter name

        Returns:
            Normalized name
        """
        # Convert to lowercase
        normalized = name.lower()

        # Remove common separators
        normalized = re.sub(r"[_-]", "", normalized)

        return normalized


__all__ = ["RequestResponseCoverageChecker"]
