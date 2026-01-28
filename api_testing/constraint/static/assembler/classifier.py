"""Classifier for categorizing request parameters.

Provides heuristic-based classification to identify parameters that
affect entire response structure (body-level) vs specific fields.
"""

from typing import Set, Dict, Optional
from api_testing.models.specification_model import ParameterProperties


class BodyParamClassifier:
    """Classifies request parameters into body-level vs detail-level.

    Uses heuristic patterns to identify parameters that affect:
    - Body-level: entire response structure (pagination, sorting, search, filtering)
    - Detail-level: specific response properties (field values, echoing)

    Attributes:
        pagination_patterns: Set of parameter name patterns for pagination
        sorting_patterns: Set of parameter name patterns for sorting
        search_patterns: Set of parameter name patterns for search/filtering
        projection_patterns: Set of parameter name patterns for field projection
    """

    # Heuristic patterns for body-level parameters
    PAGINATION_PATTERNS: Set[str] = {
        "limit",
        "offset",
        "page",
        "per_page",
        "page_size",
        "skip",
        "take",
        "top",
        "count",
        "max_results",
    }

    SORTING_PATTERNS: Set[str] = {
        "sort",
        "order",
        "order_by",
        "sort_by",
        "direction",
        "asc",
        "desc",
    }

    SEARCH_PATTERNS: Set[str] = {
        "q",
        "query",
        "search",
        "keyword",
        "term",
        "filter",
        "where",
        "filters",
    }

    PROJECTION_PATTERNS: Set[str] = {
        "fields",
        "select",
        "include",
        "exclude",
        "expand",
        "embed",
        "only",
    }

    def __init__(self, custom_body_patterns: Optional[Set[str]] = None) -> None:
        """Initialize classifier with optional custom patterns.

        Args:
            custom_body_patterns: Additional parameter name patterns
                to classify as body-level
        """
        self.custom_patterns = custom_body_patterns or set()

        # Combine all body-level patterns
        self.all_body_patterns = (
            self.PAGINATION_PATTERNS
            | self.SORTING_PATTERNS
            | self.SEARCH_PATTERNS
            | self.PROJECTION_PATTERNS
            | self.custom_patterns
        )

    def is_body_param(self, param_name: str) -> bool:
        """Check if parameter affects entire response body.

        Args:
            param_name: Parameter name to classify

        Returns:
            True if parameter is body-level, False otherwise

        Example:
            >>> classifier = BodyParamClassifier()
            >>> classifier.is_body_param("limit")
            True
            >>> classifier.is_body_param("userId")
            False
        """
        param_lower = param_name.lower()

        # Exact match
        if param_lower in self.all_body_patterns:
            return True

        # Partial match (e.g., "max_limit" contains "limit")
        for pattern in self.all_body_patterns:
            if pattern in param_lower:
                return True

        return False

    def classify_parameters(
        self, parameters: Dict[str, ParameterProperties]
    ) -> tuple[Dict[str, ParameterProperties], Dict[str, ParameterProperties]]:
        """Classify parameters into body and detail categories.

        Args:
            parameters: Dict of parameter name to ParameterProperties

        Returns:
            Tuple of (body_params, detail_params) dicts

        Example:
            >>> params = {
            ...     "limit": ParameterProperties(...),
            ...     "userId": ParameterProperties(...)
            ... }
            >>> body, detail = classifier.classify_parameters(params)
            >>> "limit" in body
            True
            >>> "userId" in detail
            True
        """
        body_params: Dict[str, ParameterProperties] = {}
        detail_params: Dict[str, ParameterProperties] = {}

        for param_name, param_props in parameters.items():
            if self.is_body_param(param_name):
                body_params[param_name] = param_props
            else:
                detail_params[param_name] = param_props

        return body_params, detail_params

    def get_param_category_hint(self, param_name: str) -> Optional[str]:
        """Get category hint for a parameter.

        Args:
            param_name: Parameter name

        Returns:
            Category hint string or None if not classified

        Example:
            >>> classifier.get_param_category_hint("limit")
            'pagination'
            >>> classifier.get_param_category_hint("sort")
            'sorting'
        """
        param_lower = param_name.lower()

        if param_lower in self.PAGINATION_PATTERNS or any(
            p in param_lower for p in self.PAGINATION_PATTERNS
        ):
            return "pagination"

        if param_lower in self.SORTING_PATTERNS or any(
            p in param_lower for p in self.SORTING_PATTERNS
        ):
            return "sorting"

        if param_lower in self.SEARCH_PATTERNS or any(
            p in param_lower for p in self.SEARCH_PATTERNS
        ):
            return "search"

        if param_lower in self.PROJECTION_PATTERNS or any(
            p in param_lower for p in self.PROJECTION_PATTERNS
        ):
            return "projection"

        return None


__all__ = ["BodyParamClassifier"]
