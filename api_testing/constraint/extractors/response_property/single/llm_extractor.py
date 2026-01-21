"""
LLM-based constraint extractor with constrained output.

Final fallback extractor that uses LLM to extract constraints
that weren't captured by structural or description extractors.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel

from api_testing.models.specification_model import ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from api_testing.constraint.primitives import (
    get_predicate,
    validate_predicate_args,
)
from api_testing.constraint.primitives.registry_loader import ProposedPredicateManager
from api_testing.constraint.extractors.prompt_builder import PredicatePromptBuilder
from common.logger import get_logger
from common.llm import ask
from common.llm.extractors import StructuredOutputExtractor
from common.llm.exceptions import LLMError


logger = get_logger(__name__)


class LLMPredicateOutput(BaseModel):
    """Output for a single predicate from LLM."""

    kind: str
    version: str
    args: Dict
    evidence: str


class LLMExtractionOutput(BaseModel):
    """LLM extraction output."""

    predicates: List[LLMPredicateOutput]


class LLMSuggestionOutput(BaseModel):
    """LLM predicate suggestion output."""

    needs_new_predicate: bool
    proposed_predicate: Dict = None
    reasoning: str = None


LLM_EXTRACTOR_USER_PROMPT = """Extract validation predicates for these missing constraints.

Field: {field_path}
Type: {field_type}
Format: {field_format}

Missing constraints to extract:
{missing_constraints}

Full description context:
"{description}"

Extract predicates for the missing constraints only."""


class ResPropSingleLLMExtractor:
    """LLM-based extractor for missing constraints.

    Uses constrained output format and validates against predicate registry.
    All extracted constraints have provenance.kind = "llm".
    """

    EXTRACTOR_NAME = "ResPropSingleLLMExtractor"

    def __init__(self, allow_suggestions: bool = True):
        """Initialize LLM extractor.

        Args:
            allow_suggestions: Whether to allow LLM to suggest new predicates
        """
        self.logger = logger
        self.allow_suggestions = allow_suggestions
        self.prompt_builder = PredicatePromptBuilder(include_all=True)
        self._system_prompt = self.prompt_builder.build_extraction_system_prompt()
        self._suggestion_prompt = self.prompt_builder.build_suggestion_system_prompt()
        self.proposal_manager = (
            ProposedPredicateManager() if allow_suggestions else None
        )

    async def extract(
        self,
        item_props: ItemProperties,
        field_path: str,
        missing_constraints: List[str],
        operation_id: str,
        array_paths: Optional[List[str]] = None,
    ) -> List[CandidateConstraint]:
        """Extract predicates for missing constraints using LLM.

        Args:
            item_props: ItemProperties for context
            field_path: Field path
            missing_constraints: List of missing constraint descriptions
            operation_id: Operation UUID for scope
            array_paths: List of array paths for JSONPath conversion

        Returns:
            List of CandidateConstraint instances
        """
        if not missing_constraints:
            return []

        # Store context for _make_predicate
        self._current_operation_id = operation_id
        self._current_array_paths = array_paths or []

        predicates: List[CandidateConstraint] = []

        try:
            # Build prompt
            missing_str = "\n".join(
                f"{i+1}. {c}" for i, c in enumerate(missing_constraints)
            )

            prompt = LLM_EXTRACTOR_USER_PROMPT.format(
                field_path=field_path,
                field_type=item_props.type or "unknown",
                field_format=item_props.format or "none",
                missing_constraints=missing_str,
                description=(
                    item_props.description[:500] if item_props.description else ""
                ),
            )

            # Call LLM
            self.logger.debug(
                "Extracting missing constraints with LLM",
                field_path=field_path,
                missing_count=len(missing_constraints),
            )

            raw_response = await ask(
                prompt=prompt,
                system=self._system_prompt,
                temperature=0.1,
                max_tokens=800,
            )

            # Extract structured output
            result: LLMExtractionOutput = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=LLMExtractionOutput,
                strict=True,
            )

            # Convert to CandidateConstraint instances
            for llm_pred in result.predicates:
                # Normalize kind - strip version if accidentally included (fixes @v1@v1 bug)
                kind = llm_pred.kind
                if "@v" in kind:
                    kind, _ = kind.split("@", 1)
                    self.logger.warning(
                        "LLM included version in kind field, normalized",
                        original=llm_pred.kind,
                        normalized=kind,
                        field_path=field_path,
                    )

                # Validate predicate exists
                meta = get_predicate(kind, llm_pred.version)
                if not meta:
                    self.logger.warning(
                        "LLM returned unknown predicate",
                        predicate=f"{kind}@{llm_pred.version}",
                        field_path=field_path,
                    )
                    continue

                # Validate args
                if not validate_predicate_args(kind, llm_pred.version, llm_pred.args):
                    self.logger.warning(
                        "LLM returned invalid args",
                        predicate=f"{kind}@{llm_pred.version}",
                        args=llm_pred.args,
                        field_path=field_path,
                    )
                    continue

                pred = self._make_predicate(
                    kind=kind,
                    version=llm_pred.version,
                    args=llm_pred.args,
                    evidence=llm_pred.evidence,
                    field_path=field_path,
                )
                if pred:
                    predicates.append(pred)

            if predicates:
                self.logger.info(
                    "LLM extraction successful",
                    field_path=field_path,
                    predicates_count=len(predicates),
                )
            else:
                self.logger.warning(
                    "LLM extraction returned no valid predicates",
                    field_path=field_path,
                    missing_count=len(missing_constraints),
                )

                # Try suggestion mode if enabled and no predicates extracted
                if self.allow_suggestions and missing_constraints:
                    await self._try_suggest_predicate(
                        item_props, field_path, missing_constraints
                    )

        except LLMError as e:
            self.logger.error(
                "LLM error during extraction",
                field_path=field_path,
                error=str(e),
            )
        except Exception as e:
            self.logger.error(
                "Error in LLM extraction",
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )

        return predicates

    def _make_predicate(
        self,
        kind: str,
        version: str,
        args: Dict,
        evidence: str,
        field_path: str,
    ) -> Optional[CandidateConstraint]:
        """Create CandidateConstraint instance.

        Args:
            kind: Predicate kind
            version: Predicate version
            args: Predicate arguments
            evidence: Evidence string
            field_path: Field path

        Returns:
            CandidateConstraint instance or None
        """
        # Check if implemented
        meta = get_predicate(kind, version)
        is_implemented = meta.implemented if meta else False
        if not is_implemented:
            self.logger.debug(
                "LLM extracted unimplemented predicate",
                predicate=f"{kind}@{version}",
                field_path=field_path,
            )

        return CandidateConstraint.from_single_field(
            field_path=field_path,
            predicate_kind=kind,
            predicate_args=args,
            operation_id=self._current_operation_id,
            extractor_name=self.EXTRACTOR_NAME,
            evidence_source="llm",
            evidence_snippet=evidence,
            confidence=0.7,  # Lower confidence for LLM extraction
            predicate_version=version,
            tags=["llm"],
            array_paths=self._current_array_paths,
        )

    async def _try_suggest_predicate(
        self,
        item_props: ItemProperties,
        field_path: str,
        missing_constraints: List[str],
    ) -> None:
        """Try to suggest a new predicate for unmatched constraints.

        Args:
            item_props: ItemProperties for context
            field_path: Field path
            missing_constraints: Constraints that couldn't be extracted
        """
        if not self.proposal_manager:
            return

        try:
            # Build suggestion prompt
            constraint_text = "\n".join(f"- {c}" for c in missing_constraints)

            prompt = f"""Field: {field_path}
Type: {item_props.type or "unknown"}
Description: {item_props.description[:300] if item_props.description else "N/A"}

The following constraints cannot be expressed with existing predicates:
{constraint_text}

Design a new predicate to handle these constraints."""

            self.logger.debug(
                "Asking LLM to suggest new predicate",
                field_path=field_path,
            )

            raw_response = await ask(
                prompt=prompt,
                system=self._suggestion_prompt,
                temperature=0.2,
                max_tokens=600,
            )

            # Extract structured output
            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=LLMSuggestionOutput,
                strict=True,
            )

            if result.needs_new_predicate and result.proposed_predicate:
                pred = result.proposed_predicate

                # Validate required fields
                if all(
                    k in pred
                    for k in [
                        "kind",
                        "version",
                        "category",
                        "description",
                        "args_schema",
                    ]
                ):
                    # Add proposal to registry
                    success = self.proposal_manager.add_proposal(
                        kind=pred["kind"],
                        version=pred.get("version", "v1"),
                        category=pred["category"],
                        description=pred["description"],
                        args_schema=pred["args_schema"],
                        evidence=result.reasoning
                        or f"Proposed for constraints: {constraint_text[:200]}",
                        field_context=field_path,
                        proposed_by="llm",
                    )

                    if success:
                        self.logger.info(
                            "LLM suggested new predicate",
                            predicate=f"{pred['kind']}@{pred.get('version', 'v1')}",
                            field_path=field_path,
                        )

        except LLMError as e:
            self.logger.error(
                "LLM error during predicate suggestion",
                field_path=field_path,
                error=str(e),
            )
        except Exception as e:
            self.logger.error(
                "Error in predicate suggestion",
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )


__all__ = ["ResPropSingleLLMExtractor"]
