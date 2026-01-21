"""
Structural constraint extractor.

Deterministically extracts constraints from OpenAPI schema structural keywords.
Maps JSON Schema properties directly to validation predicates with 100% confidence.
"""

from typing import List, Dict, Optional

from api_testing.models.specification_model import ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from api_testing.constraint.primitives import (
    get_predicate,
    validate_predicate_args,
)
from common.logger import get_logger

logger = get_logger(__name__)


class ResPropSingleStructuralExtractor:
    """Extracts constraints from OpenAPI schema structural properties.

    Deterministic extraction from:
    - type + enum → int.enum@v1 or string.enum@v1
    - type + minimum/maximum → int.range@v1
    - type=string + format=date → date.iso_date@v1
    - type=string + pattern → string.pattern@v1
    - type=array + minItems/maxItems → array.length@v1
    - etc.

    All extracted constraints have:
    - provenance.kind = "schema_structural"
    - provenance.confidence = 1.0 (deterministic)
    """

    EXTRACTOR_NAME = "ResPropSingleStructuralExtractor"

    def __init__(self):
        """Initialize structural extractor."""
        self.logger = logger

    def extract(
        self,
        item_props: ItemProperties,
        field_path: str,
        operation_id: str,
        array_paths: Optional[List[str]] = None,
    ) -> List[CandidateConstraint]:
        """Extract predicates from ItemProperties.

        Args:
            item_props: OpenAPI schema properties
            field_path: Field path (for logging/evidence)
            operation_id: Operation UUID for scope
            array_paths: List of array paths for JSONPath conversion

        Returns:
            List of CandidateConstraint instances
        """
        if not item_props:
            return []

        # Store context for _make_predicate
        self._current_operation_id = operation_id
        self._current_array_paths = array_paths or []

        predicates: List[CandidateConstraint] = []

        try:
            # Extract based on type
            if item_props.type == "integer":
                predicates.extend(self._extract_integer(item_props, field_path))
            elif item_props.type == "string":
                predicates.extend(self._extract_string(item_props, field_path))
            elif item_props.type == "number":
                predicates.extend(self._extract_number(item_props, field_path))
            elif item_props.type == "boolean":
                predicates.extend(self._extract_boolean(item_props, field_path))
            elif item_props.type == "array":
                predicates.extend(self._extract_array(item_props, field_path))

            if predicates:
                self.logger.debug(
                    "Structural extraction successful",
                    field_path=field_path,
                    type=item_props.type,
                    predicates_count=len(predicates),
                )
        except Exception as e:
            self.logger.error(
                "Error in structural extraction",
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )

        return predicates

    def _extract_integer(
        self, item_props: ItemProperties, field_path: str
    ) -> List[CandidateConstraint]:
        """Extract integer constraints."""
        predicates: List[CandidateConstraint] = []

        # Priority: binary format > enum > range
        # Binary format indicates 0/1 boolean-like integers
        if item_props.format == "binary":
            pred = self._make_predicate(
                kind="int.enum",
                args={"values": [0, 1]},
                evidence="format: binary",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)
        elif item_props.enum and len(item_props.enum) > 0:
            # Validate enum values are integers
            if all(
                isinstance(v, int) and not isinstance(v, bool) for v in item_props.enum
            ):
                pred = self._make_predicate(
                    kind="int.enum",
                    args={"values": item_props.enum},
                    evidence=f"enum: {item_props.enum}",
                    field_path=field_path,
                )
                if pred:
                    predicates.append(pred)
        elif item_props.minimum is not None or item_props.maximum is not None:
            args = {}
            evidence_parts = []

            if item_props.minimum is not None:
                args["min"] = item_props.minimum
                evidence_parts.append(f"minimum: {item_props.minimum}")
            if item_props.maximum is not None:
                args["max"] = item_props.maximum
                evidence_parts.append(f"maximum: {item_props.maximum}")

            pred = self._make_predicate(
                kind="int.range",
                args=args,
                evidence=", ".join(evidence_parts),
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        return predicates

    def _extract_string(
        self, item_props: ItemProperties, field_path: str
    ) -> List[CandidateConstraint]:
        """Extract string constraints."""
        predicates: List[CandidateConstraint] = []

        # Enum
        if item_props.enum and len(item_props.enum) > 0:
            if all(isinstance(v, str) for v in item_props.enum):
                pred = self._make_predicate(
                    kind="string.enum",
                    args={"values": item_props.enum},
                    evidence=f"enum: {item_props.enum[:5]}{'...' if len(item_props.enum) > 5 else ''}",
                    field_path=field_path,
                )
                if pred:
                    predicates.append(pred)

        # Format: date
        if item_props.format == "date":
            pred = self._make_predicate(
                kind="date.iso_date",
                args={},
                evidence="format: date",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        # Format: date-time
        if item_props.format in ["date-time", "datetime"]:
            pred = self._make_predicate(
                kind="date.iso_datetime",
                args={},
                evidence=f"format: {item_props.format}",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        # Format: uri
        if item_props.format == "uri":
            pred = self._make_predicate(
                kind="string.uri",
                args={},
                evidence="format: uri",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        # Format: email
        if item_props.format == "email":
            pred = self._make_predicate(
                kind="string.email",
                args={},
                evidence="format: email",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        # Format: uuid
        if item_props.format == "uuid":
            pred = self._make_predicate(
                kind="string.uuid",
                args={},
                evidence="format: uuid",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        # Pattern
        if item_props.pattern:
            pred = self._make_predicate(
                kind="string.pattern",
                args={"pattern": item_props.pattern},
                evidence=f"pattern: {item_props.pattern}",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        # Length constraints
        if item_props.min_length is not None or item_props.max_length is not None:
            args = {}
            evidence_parts = []

            if item_props.min_length is not None:
                args["min"] = item_props.min_length
                evidence_parts.append(f"minimum length: {item_props.min_length}")
            if item_props.max_length is not None:
                args["max"] = item_props.max_length
                evidence_parts.append(f"maximum length: {item_props.max_length}")

            pred = self._make_predicate(
                kind="string.length",
                args=args,
                evidence=", ".join(evidence_parts),
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        return predicates

    def _extract_number(
        self, item_props: ItemProperties, field_path: str
    ) -> List[CandidateConstraint]:
        """Extract number (float/double) constraints."""
        predicates: List[CandidateConstraint] = []

        # Range
        if item_props.minimum is not None or item_props.maximum is not None:
            args = {}
            evidence_parts = []

            if item_props.minimum is not None:
                args["min"] = item_props.minimum
                evidence_parts.append(f"minimum: {item_props.minimum}")
            if item_props.maximum is not None:
                args["max"] = item_props.maximum
                evidence_parts.append(f"maximum: {item_props.maximum}")

            pred = self._make_predicate(
                kind="number.range",
                args=args,
                evidence=", ".join(evidence_parts),
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        return predicates

    def _extract_boolean(
        self, item_props: ItemProperties, field_path: str
    ) -> List[CandidateConstraint]:
        """Extract boolean constraints."""
        predicates: List[CandidateConstraint] = []

        # Const value
        if item_props.default is not None and isinstance(item_props.default, bool):
            pred = self._make_predicate(
                kind="boolean.default",
                args={"value": item_props.default},
                evidence=f"default: {item_props.default}",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        return predicates

    def _extract_array(
        self, item_props: ItemProperties, field_path: str
    ) -> List[CandidateConstraint]:
        """Extract array constraints."""
        predicates: List[CandidateConstraint] = []

        # Length constraints
        if item_props.minItems is not None or item_props.maxItems is not None:
            args = {}
            evidence_parts = []

            if item_props.minItems is not None:
                args["min"] = item_props.minItems
                evidence_parts.append(f"minItems: {item_props.minItems}")
            if item_props.maxItems is not None:
                args["max"] = item_props.maxItems
                evidence_parts.append(f"maxItems: {item_props.maxItems}")

            pred = self._make_predicate(
                kind="array.length",
                args=args,
                evidence=", ".join(evidence_parts),
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        # Unique items
        if item_props.uniqueItems is True:
            pred = self._make_predicate(
                kind="array.unique",
                args={},
                evidence="uniqueItems: true",
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        return predicates

    def _make_predicate(
        self,
        kind: str,
        args: Dict,
        evidence: str,
        field_path: str,
    ) -> Optional[CandidateConstraint]:
        """Create CandidateConstraint instance.

        Args:
            kind: Predicate kind
            args: Predicate arguments
            evidence: Evidence string from schema
            field_path: Field path

        Returns:
            CandidateConstraint instance or None if invalid
        """
        version = "v1"

        # Validate args if predicate exists in registry
        meta = get_predicate(kind, version)
        if meta and not validate_predicate_args(kind, version, args):
            self.logger.warning(
                "Invalid predicate args (skipping)",
                predicate=f"{kind}@{version}",
                args=args,
                field_path=field_path,
            )
            return None

        # Check if implemented
        is_implemented = meta.implemented if meta else False
        if not is_implemented:
            self.logger.debug(
                "Predicate not implemented (will be created but may fail at runtime)",
                predicate=f"{kind}@{version}",
                field_path=field_path,
            )

        return CandidateConstraint.from_single_field(
            field_path=field_path,
            predicate_kind=kind,
            predicate_args=args,
            operation_id=self._current_operation_id,
            extractor_name=self.EXTRACTOR_NAME,
            evidence_source="schema",
            evidence_snippet=evidence,
            confidence=1.0,
            predicate_version=version,
            tags=["structural"],
            array_paths=self._current_array_paths,
        )

    def can_extract(self, item_props: ItemProperties) -> bool:
        """Check if extractor can extract anything from ItemProperties.

        Args:
            item_props: ItemProperties to check

        Returns:
            True if at least one constraint can be extracted
        """
        if not item_props:
            return False

        # Check for extractable properties
        has_constraints = (
            (item_props.enum and len(item_props.enum) > 0)
            or item_props.minimum is not None
            or item_props.maximum is not None
            or item_props.min_length is not None
            or item_props.max_length is not None
            or item_props.format
            in ["date", "date-time", "datetime", "uri", "email", "uuid", "binary"]
            or item_props.pattern is not None
            or item_props.min_items is not None
            or item_props.max_items is not None
            or item_props.unique_items is True
            or item_props.default is not None
        )

        return has_constraints


__all__ = ["ResPropSingleStructuralExtractor"]
