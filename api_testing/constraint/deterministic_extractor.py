"""
Deterministic constraint extractor.

Extracts constraint predicates from ItemProperties without using LLM.
Maps structured OpenAPI schema fields directly to validation predicates.
"""

from typing import List, Optional
from api_testing.models.specification_model import ItemProperties
from api_testing.validation.models import PredicateModel
from common.logger import get_logger

logger = get_logger(__name__)


class DeterministicExtractor:
    """Extract validation predicates from ItemProperties deterministically.

    Maps OpenAPI schema constraints to validation predicates:
    - type + enum → int.enum@v1 or string.enum@v1
    - type + minimum/maximum → int.range@v1
    - format=date → date.iso_date@v1
    - pattern → string.pattern@v1

    Example:
        >>> extractor = DeterministicExtractor()
        >>> item = ItemProperties(type="integer", minimum=1, maximum=32)
        >>> predicates = extractor.extract_predicates(item, "holidays[].id")
        >>> predicates[0].kind
        'int.range'
    """

    def __init__(self):
        """Initialize deterministic extractor."""
        self.logger = logger

    def extract_predicates(
        self, item_props: ItemProperties, field_path: str
    ) -> List[PredicateModel]:
        """Extract predicates from ItemProperties.

        Args:
            item_props: ItemProperties object containing schema information
            field_path: Dot notation path to field (for logging)

        Returns:
            List of PredicateModel objects (may be empty)
        """
        if item_props is None:
            return []

        predicates = []

        try:
            # Handle integer type
            if item_props.type == "integer":
                predicates.extend(self._extract_integer_predicates(item_props))

            # Handle string type
            elif item_props.type == "string":
                predicates.extend(self._extract_string_predicates(item_props))

            # Handle number type (float/double)
            elif item_props.type == "number":
                predicates.extend(self._extract_number_predicates(item_props))

            # Object and array types don't have direct validators
            # (their properties/items are validated recursively)

            if predicates:
                self.logger.debug(
                    f"Extracted predicates",
                    field_path=field_path,
                    type=item_props.type,
                    predicates_count=len(predicates),
                )

        except Exception as e:
            self.logger.error(
                f"Error extracting predicates",
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )

        return predicates

    def _extract_integer_predicates(
        self, item_props: ItemProperties
    ) -> List[PredicateModel]:
        """Extract predicates for integer type.

        Priority: enum > range > nothing
        """
        predicates = []

        # Check for enum (highest priority)
        if item_props.enum and len(item_props.enum) > 0:
            predicates.append(
                PredicateModel(
                    kind="int.enum", version="v1", args={"values": item_props.enum}
                )
            )
            return predicates  # Enum is most specific, skip range

        # Check for range constraints
        if item_props.minimum is not None or item_props.maximum is not None:
            args = {}
            if item_props.minimum is not None:
                args["min"] = item_props.minimum
            if item_props.maximum is not None:
                args["max"] = item_props.maximum

            predicates.append(PredicateModel(kind="int.range", version="v1", args=args))

        return predicates

    def _extract_string_predicates(
        self, item_props: ItemProperties
    ) -> List[PredicateModel]:
        """Extract predicates for string type.

        Can have multiple predicates (e.g., enum + format).
        """
        predicates = []

        # Check for enum
        if item_props.enum and len(item_props.enum) > 0:
            # Ensure all enum values are strings
            if all(isinstance(v, str) for v in item_props.enum):
                predicates.append(
                    PredicateModel(
                        kind="string.enum",
                        version="v1",
                        args={"values": item_props.enum},
                    )
                )

        # Check for date format
        if item_props.format == "date":
            predicates.append(
                PredicateModel(kind="date.iso_date", version="v1", args={})
            )

        # Check for pattern
        if item_props.pattern:
            predicates.append(
                PredicateModel(
                    kind="string.pattern",
                    version="v1",
                    args={"pattern": item_props.pattern},
                )
            )

        return predicates

    def _extract_number_predicates(
        self, item_props: ItemProperties
    ) -> List[PredicateModel]:
        """Extract predicates for number type (float/double).

        Similar to integer but for floating-point numbers.
        Note: We don't have number validators in Phase 1 (only 5 core validators).
        This method is a placeholder for future expansion.
        """
        predicates = []

        # TODO: Implement number.range@v1 validator in future phase
        # For now, log that we're skipping number validation
        if item_props.minimum is not None or item_props.maximum is not None:
            self.logger.debug(
                "Number type constraints detected but number validators not yet implemented",
                minimum=item_props.minimum,
                maximum=item_props.maximum,
            )

        return predicates

    def can_extract(self, item_props: ItemProperties) -> bool:
        """Check if extractor can extract predicates from ItemProperties.

        Args:
            item_props: ItemProperties to check

        Returns:
            True if extractor can extract at least one predicate
        """
        if item_props is None:
            return False

        # Check if any extractable constraints exist
        has_constraints = (
            (
                item_props.type == "integer"
                and (
                    item_props.enum
                    or item_props.minimum is not None
                    or item_props.maximum is not None
                )
            )
            or (
                item_props.type == "string"
                and (
                    item_props.enum or item_props.format == "date" or item_props.pattern
                )
            )
            or (
                item_props.type == "number"
                and (item_props.minimum is not None or item_props.maximum is not None)
            )
        )

        return has_constraints


__all__ = ["DeterministicExtractor"]
