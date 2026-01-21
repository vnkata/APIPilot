"""
Heuristic cross-field extractor for detecting common field relationship patterns.

Detects deterministic patterns without LLM:
- Date comparisons (startDate < endDate, createdAt < updatedAt)
- Numeric comparisons (minValue < maxValue, price > discountedPrice)
- Timestamp relationships (created < updated)
"""

from typing import List, Dict, Optional
import re

from api_testing.models.specification_model import ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from common.logger import get_logger

logger = get_logger(__name__)


class ResPropHeuristicCrossFieldExtractor:
    """Detects common cross-field patterns without LLM.

    Uses naming patterns and type information to identify likely relationships.
    """

    def __init__(self):
        """Initialize heuristic extractor."""
        self.logger = logger

        # Common date/time field patterns
        self.date_patterns = [
            (
                r"^start(.*)$",
                r"^end(.*)$",
                "less_than_or_equal",
            ),  # startDate <= endDate
            (r"^begin(.*)$", r"^finish(.*)$", "less_than_or_equal"),
            (r"^from(.*)$", r"^to(.*)$", "less_than_or_equal"),
            (
                r"^created(.*)$",
                r"^updated(.*)$",
                "less_than_or_equal",
            ),  # created <= updated
            (r"^created(.*)$", r"^modified(.*)$", "less_than_or_equal"),
            (r"^(.*)_start$", r"^(.*)_end$", "less_than_or_equal"),
        ]

        # Common numeric field patterns
        self.numeric_patterns = [
            (r"^min(.*)$", r"^max(.*)$", "less_than_or_equal"),  # minValue <= maxValue
            (r"^minimum(.*)$", r"^maximum(.*)$", "less_than_or_equal"),
            (r"^lower(.*)$", r"^upper(.*)$", "less_than_or_equal"),
            (r"^(.*)_min$", r"^(.*)_max$", "less_than_or_equal"),
        ]

        # Price-specific patterns
        self.price_patterns = [
            (
                "price",
                "discountedPrice",
                "greater_than_or_equal",
            ),  # price >= discountedPrice
            ("price", "salePrice", "greater_than_or_equal"),
            ("originalPrice", "price", "greater_than_or_equal"),
            ("regularPrice", "salePrice", "greater_than_or_equal"),
        ]

    def extract(
        self,
        response_schema: ItemProperties,
        operation_id: Optional[str] = None,
    ) -> List[CandidateConstraint]:
        """Extract cross-field constraints using heuristics.

        Args:
            response_schema: Response schema to analyze
            operation_id: Optional operation ID for context

        Returns:
            List of candidate constraints
        """
        candidates = []

        if not response_schema or not response_schema.properties:
            return candidates

        # Flatten schema to get all fields
        flattened = self._flatten_schema(response_schema)

        if len(flattened) < 2:
            # Need at least 2 fields for cross-field relationships
            return candidates

        # Extract date/time comparisons
        candidates.extend(self._extract_date_comparisons(flattened, operation_id))

        # Extract numeric comparisons
        candidates.extend(self._extract_numeric_comparisons(flattened, operation_id))

        # Extract price relationships
        candidates.extend(self._extract_price_relationships(flattened, operation_id))

        self.logger.info(
            f"Heuristic cross-field extraction found {len(candidates)} candidates",
            operation=operation_id or "unknown",
        )

        return candidates

    def _flatten_schema(
        self,
        schema: ItemProperties,
        prefix: str = "",
    ) -> Dict[str, Dict]:
        """Flatten schema into field_path -> field_info mapping.

        Args:
            schema: Schema to flatten
            prefix: Path prefix

        Returns:
            Dict of field_path -> field_info
        """
        result = {}

        if not schema or not schema.properties:
            return result

        for field_name, field_schema in schema.properties.items():
            field_path = f"{prefix}.{field_name}" if prefix else field_name

            # Store field info
            result[field_path] = {
                "type": field_schema.type,
                "format": field_schema.format,
                "description": field_schema.description or "",
                "schema": field_schema,
            }

            # Recursively flatten nested objects (but not arrays)
            if field_schema.type == "object" and field_schema.properties:
                nested = self._flatten_schema(field_schema, field_path)
                result.update(nested)

        return result

    def _extract_date_comparisons(
        self,
        flattened: Dict[str, Dict],
        operation_id: Optional[str],
    ) -> List[CandidateConstraint]:
        """Extract date/time field comparisons.

        Args:
            flattened: Flattened field mapping
            operation_id: Operation ID

        Returns:
            List of candidate constraints
        """
        candidates = []

        # Get date/time fields
        date_fields = {
            path: info for path, info in flattened.items() if self._is_date_field(info)
        }

        if len(date_fields) < 2:
            return candidates

        # Check each pattern
        for start_pattern, end_pattern, relationship in self.date_patterns:
            for field_a_path, field_a_info in date_fields.items():
                field_a_name = field_a_path.split(".")[-1]
                start_match = re.match(start_pattern, field_a_name, re.IGNORECASE)

                if not start_match:
                    continue

                base_name = start_match.group(1) if start_match.lastindex else ""

                # Find matching end field
                for field_b_path, field_b_info in date_fields.items():
                    if field_b_path == field_a_path:
                        continue

                    field_b_name = field_b_path.split(".")[-1]
                    end_match = re.match(end_pattern, field_b_name, re.IGNORECASE)

                    if not end_match:
                        continue

                    end_base = end_match.group(1) if end_match.lastindex else ""

                    # Check if base names match (or both empty)
                    if base_name.lower() == end_base.lower():
                        # Check if at same nesting level
                        if field_a_path.count(".") == field_b_path.count("."):
                            candidate = self._create_comparison_candidate(
                                field_a_path,
                                field_b_path,
                                relationship,
                                "date",
                                operation_id,
                                confidence=0.9,
                                evidence=f"Date pattern: {field_a_name} {relationship} {field_b_name}",
                            )
                            candidates.append(candidate)
                            break  # Found match for this field

        return candidates

    def _extract_numeric_comparisons(
        self,
        flattened: Dict[str, Dict],
        operation_id: Optional[str],
    ) -> List[CandidateConstraint]:
        """Extract numeric field comparisons.

        Args:
            flattened: Flattened field mapping
            operation_id: Operation ID

        Returns:
            List of candidate constraints
        """
        candidates = []

        # Get numeric fields
        numeric_fields = {
            path: info
            for path, info in flattened.items()
            if info.get("type") in ["integer", "number"]
        }

        if len(numeric_fields) < 2:
            return candidates

        # Check each pattern
        for min_pattern, max_pattern, relationship in self.numeric_patterns:
            for field_a_path, field_a_info in numeric_fields.items():
                field_a_name = field_a_path.split(".")[-1]
                min_match = re.match(min_pattern, field_a_name, re.IGNORECASE)

                if not min_match:
                    continue

                base_name = min_match.group(1) if min_match.lastindex else ""

                # Find matching max field
                for field_b_path, field_b_info in numeric_fields.items():
                    if field_b_path == field_a_path:
                        continue

                    field_b_name = field_b_path.split(".")[-1]
                    max_match = re.match(max_pattern, field_b_name, re.IGNORECASE)

                    if not max_match:
                        continue

                    max_base = max_match.group(1) if max_match.lastindex else ""

                    # Check if base names match
                    if base_name.lower() == max_base.lower():
                        # Check if at same nesting level
                        if field_a_path.count(".") == field_b_path.count("."):
                            candidate = self._create_comparison_candidate(
                                field_a_path,
                                field_b_path,
                                relationship,
                                "numeric",
                                operation_id,
                                confidence=0.9,
                                evidence=f"Numeric pattern: {field_a_name} {relationship} {field_b_name}",
                            )
                            candidates.append(candidate)
                            break

        return candidates

    def _extract_price_relationships(
        self,
        flattened: Dict[str, Dict],
        operation_id: Optional[str],
    ) -> List[CandidateConstraint]:
        """Extract price-specific relationships.

        Args:
            flattened: Flattened field mapping
            operation_id: Operation ID

        Returns:
            List of candidate constraints
        """
        candidates = []

        # Get numeric fields (prices are typically numeric)
        numeric_fields = {
            path: info
            for path, info in flattened.items()
            if info.get("type") in ["integer", "number"]
        }

        if len(numeric_fields) < 2:
            return candidates

        # Check each price pattern
        for (
            field_a_name_pattern,
            field_b_name_pattern,
            relationship,
        ) in self.price_patterns:
            # Find fields matching patterns
            field_a_candidates = [
                (path, info)
                for path, info in numeric_fields.items()
                if field_a_name_pattern.lower() in path.split(".")[-1].lower()
            ]

            field_b_candidates = [
                (path, info)
                for path, info in numeric_fields.items()
                if field_b_name_pattern.lower() in path.split(".")[-1].lower()
            ]

            # Match pairs at same nesting level
            for field_a_path, field_a_info in field_a_candidates:
                for field_b_path, field_b_info in field_b_candidates:
                    if field_a_path == field_b_path:
                        continue

                    # Check if at same nesting level
                    if field_a_path.count(".") == field_b_path.count("."):
                        # Check if similar parent paths
                        parent_a = ".".join(field_a_path.split(".")[:-1])
                        parent_b = ".".join(field_b_path.split(".")[:-1])

                        if parent_a == parent_b:
                            candidate = self._create_comparison_candidate(
                                field_a_path,
                                field_b_path,
                                relationship,
                                "numeric",
                                operation_id,
                                confidence=0.85,
                                evidence=f"Price pattern: {field_a_path.split('.')[-1]} {relationship} {field_b_path.split('.')[-1]}",
                            )
                            candidates.append(candidate)

        return candidates

    def _is_date_field(self, field_info: Dict) -> bool:
        """Check if field is a date/time field.

        Args:
            field_info: Field information

        Returns:
            True if date/time field
        """
        field_format = field_info.get("format", "")
        field_type = field_info.get("type", "")

        # Check format
        if field_format in ["date", "date-time", "datetime", "time"]:
            return True

        # Check type for string dates
        if field_type == "string":
            description = field_info.get("description", "").lower()
            if any(kw in description for kw in ["date", "time", "timestamp"]):
                return True

        return False

    def _create_comparison_candidate(
        self,
        field_a: str,
        field_b: str,
        relationship: str,
        comparison_type: str,
        operation_id: Optional[str],
        confidence: float,
        evidence: str,
    ) -> CandidateConstraint:
        """Create a comparison candidate constraint.

        Args:
            field_a: First field path
            field_b: Second field path
            relationship: Relationship type
            comparison_type: Type of comparison (date/numeric)
            operation_id: Operation ID
            confidence: Confidence score
            evidence: Evidence string

        Returns:
            CandidateConstraint
        """
        # Map relationship to predicate kind
        predicate_map = {
            "less_than": "comparison.less_than",
            "less_than_or_equal": "comparison.less_than_or_equal",
            "greater_than": "comparison.greater_than",
            "greater_than_or_equal": "comparison.greater_than_or_equal",
            "equals": "comparison.equals",
        }

        predicate_kind = predicate_map.get(
            relationship, "comparison.less_than_or_equal"
        )

        candidate = CandidateConstraint(
            predicate_kind=predicate_kind,
            predicate_version="v1",
            predicate_args={"comparison_type": comparison_type},
            selectors=[
                f"$response.body$.{field_a}",
                f"$response.body$.{field_b}",
            ],
            selector_types=["jsonpath", "jsonpath"],
            operation_id=operation_id or "unknown",
            phase="response",
            location="body",
            confidence=confidence,
            tags=["cross_field", "heuristic", relationship, comparison_type],
            extractor_name="HeuristicCrossFieldExtractor",
        )

        candidate.add_evidence(
            source="heuristic",
            location=f"response.{field_a},{field_b}",
            snippet=evidence,
            confidence=confidence,
        )

        return candidate


__all__ = ["ResPropHeuristicCrossFieldExtractor"]
