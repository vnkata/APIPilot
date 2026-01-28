"""
Description-based constraint extractor.

Extracts constraints from natural language descriptions using:
1. Pattern catalog (rule-based, high precision)
2. LLM fallback (for patterns not in catalog)
"""

from typing import List, Dict, Optional

from api_testing.models.specification_model import ItemProperties
from api_testing.constraint.ir.extractors.common import CandidateConstraint
from api_testing.constraint.ir.extractors.common import match_patterns
from api_testing.constraint.ir.extractors.prompt_builder import PredicatePromptBuilder
from api_testing.constraint.ir.primitives import (
    get_predicate,
    validate_predicate_args,
)
from common.logger import get_logger
from common.llm import ask
from common.llm.extractors import StructuredOutputExtractor
from common.llm.exceptions import LLMError
from pydantic import BaseModel


logger = get_logger(__name__)


class ResPropSinglePredicateOutput(BaseModel):
    """LLM output for single predicate."""

    kind: str
    version: str
    args: Dict


class ResPropSingleDescriptionExtractionOutput(BaseModel):
    """LLM output for description extraction."""

    predicates: List[ResPropSinglePredicateOutput]


LLM_DESCRIPTION_USER_PROMPT = """Extract validation constraints from this description:

Description: "{description}"
Field type: {field_type}
Field format: {field_format}

Return JSON with predicates array."""


class ResPropSingleDescriptionExtractor:
    """Extracts constraints from field descriptions.

    Uses pattern catalog first (high precision), then falls back to LLM
    for descriptions that don't match known patterns.

    All extracted constraints have:
    - provenance.kind = "schema_description"
    - provenance.confidence varies (0.7-0.95) based on method
    """

    EXTRACTOR_NAME = "ResPropSingleDescriptionExtractor"

    def __init__(self, use_llm_fallback: bool = True):
        """Initialize description extractor.

        Args:
            use_llm_fallback: Whether to use LLM if patterns don't match
        """
        self._current_array_paths = None
        self._current_operation_id = None
        self.use_llm_fallback = use_llm_fallback
        self.logger = logger
        self.prompt_builder = PredicatePromptBuilder(include_all=True)
        self._system_prompt = self.prompt_builder.build_description_extraction_prompt()

    async def extract(
        self,
        item_props: ItemProperties,
        field_path: str,
        operation_id: str,
        array_paths: Optional[List[str]] = None,
    ) -> List[CandidateConstraint]:
        """Extract predicates from description.

        Args:
            item_props: ItemProperties with description
            field_path: Field path (for logging)
            operation_id: Operation UUID for scope
            array_paths: List of array paths for JSONPath conversion

        Returns:
            List of CandidateConstraint instances
        """
        description = item_props.description
        if not description or not description.strip():
            return []

        # Store context for _make_predicate
        self._current_operation_id = operation_id
        self._current_array_paths = array_paths or []

        predicates: List[CandidateConstraint] = []

        try:
            # Phase 1: Try pattern matching (rule-based)
            pattern_predicates = self._extract_with_patterns(
                description, item_props, field_path
            )
            predicates.extend(pattern_predicates)

            # Phase 2: LLM fallback if no patterns matched and LLM enabled
            if not predicates and self.use_llm_fallback:
                llm_predicates = await self._extract_with_llm(
                    description, item_props, field_path
                )
                predicates.extend(llm_predicates)

            if predicates:
                self.logger.debug(
                    "Description extraction successful",
                    field_path=field_path,
                    predicates_count=len(predicates),
                    method="patterns" if pattern_predicates else "llm",
                )
        except Exception as e:
            self.logger.error(
                "Error in description extraction",
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )

        return predicates

    def _extract_with_patterns(
        self,
        description: str,
        item_props: ItemProperties,
        field_path: str,
    ) -> List[CandidateConstraint]:
        """Extract using pattern catalog (rule-based).

        Args:
            description: Description text
            item_props: ItemProperties for type context
            field_path: Field path

        Returns:
            List of CandidateConstraint instances
        """
        predicates: List[CandidateConstraint] = []

        # Match patterns
        matches = match_patterns(description, field_type=item_props.type)

        for pattern, args, evidence in matches:
            # Validate args
            if not validate_predicate_args(pattern.predicate_kind, "v1", args):
                self.logger.warning(
                    "Pattern matched but args invalid",
                    pattern=pattern.name,
                    args=args,
                    field_path=field_path,
                )
                continue

            pred = self._make_predicate(
                kind=pattern.predicate_kind,
                args=args,
                confidence=pattern.confidence,
                evidence=evidence,
                field_path=field_path,
            )
            if pred:
                predicates.append(pred)

        return predicates

    async def _extract_with_llm(
        self,
        description: str,
        item_props: ItemProperties,
        field_path: str,
    ) -> List[CandidateConstraint]:
        """Extract using LLM (fallback).

        Args:
            description: Description text
            item_props: ItemProperties for context
            field_path: Field path

        Returns:
            List of CandidateConstraint instances
        """
        predicates: List[CandidateConstraint] = []

        try:
            # Build prompt
            prompt = LLM_DESCRIPTION_USER_PROMPT.format(
                description=description[:500],  # Limit length
                field_type=item_props.type or "unknown",
                field_format=item_props.format or "none",
            )

            # Call LLM
            self.logger.debug(
                "Calling LLM for description extraction",
                field_path=field_path,
                description_preview=description[:100],
            )

            raw_response = await ask(
                prompt=prompt,
                system=self._system_prompt,
                temperature=0.1,
                max_tokens=500,
            )

            # Extract structured output
            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=ResPropSingleDescriptionExtractionOutput,
                strict=True,
            )

            # Convert to CandidateConstraint instances
            for pred_output in result.predicates:
                # Normalize kind - strip version if accidentally included (fixes @v1@v1 bug)
                kind = pred_output.kind
                if "@v" in kind:
                    kind, _ = kind.split("@", 1)
                    self.logger.warning(
                        "LLM included version in kind field, normalized",
                        original=pred_output.kind,
                        normalized=kind,
                        field_path=field_path,
                    )

                # Validate args
                if not validate_predicate_args(
                    kind, pred_output.version, pred_output.args
                ):
                    self.logger.warning(
                        "LLM returned invalid args",
                        predicate=f"{kind}@{pred_output.version}",
                        args=pred_output.args,
                        field_path=field_path,
                    )
                    continue

                pred = self._make_predicate(
                    kind=kind,
                    args=pred_output.args,
                    confidence=0.75,  # Lower confidence for LLM extraction
                    evidence=f"LLM extracted from: {description[:100]}...",
                    field_path=field_path,
                )
                if pred:
                    predicates.append(pred)

            if predicates:
                self.logger.info(
                    "LLM description extraction succeeded",
                    field_path=field_path,
                    predicates_count=len(predicates),
                )

        except LLMError as e:
            self.logger.error(
                "LLM error during description extraction",
                field_path=field_path,
                error=str(e),
            )
        except Exception as e:
            self.logger.error(
                "Error in LLM description extraction",
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )

        return predicates

    def _make_predicate(
        self,
        kind: str,
        args: Dict,
        confidence: float,
        evidence: str,
        field_path: str,
    ) -> Optional[CandidateConstraint]:
        """Create CandidateConstraint instance.

        Args:
            kind: Predicate kind
            args: Predicate arguments
            confidence: Confidence score
            evidence: Evidence string
            field_path: Field path

        Returns:
            CandidateConstraint instance or None
        """
        version = "v1"

        # Check if implemented
        meta = get_predicate(kind, version)
        is_implemented = meta.implemented if meta else False
        if not is_implemented:
            self.logger.debug(
                "Predicate not implemented",
                predicate=f"{kind}@{version}",
                field_path=field_path,
            )

        return CandidateConstraint.from_single_field(
            field_path=field_path,
            predicate_kind=kind,
            predicate_args=args,
            operation_id=self._current_operation_id,
            extractor_name=self.EXTRACTOR_NAME,
            evidence_source="description",
            evidence_snippet=evidence,
            confidence=confidence,
            predicate_version=version,
            tags=["description"],
            array_paths=self._current_array_paths,
        )


__all__ = ["ResPropSingleDescriptionExtractor"]
