"""
LLM coverage checker for constraint extraction.

Uses LLM-driven decision approach: shows LLM existing constraints and asks
if they sufficiently cover the description requirements.
"""

from api_testing.constraint.ir.extractors.common import CoverageCheckResult
from api_testing.constraint.ir.extractors.prompt_builder import PredicatePromptBuilder
from api_testing.models.specification_model import ItemProperties
from common.llm import ask
from common.llm.exceptions import LLMError
from common.llm.extractors import StructuredOutputExtractor
from common.logger import get_logger

logger = get_logger(__name__)


class ResPropSingleCoverageChecker:
    """Check coverage of extracted constraints using LLM-driven decision.

    Uses PredicatePromptBuilder for centralized prompt management and
    CoverageCheckResult model for structured output.
    """

    def __init__(self):
        """Initialize coverage checker with prompt builder."""
        self.logger = logger
        self.prompt_builder = PredicatePromptBuilder()

    async def check_coverage(
        self,
        item_props: ItemProperties,
        field_path: str,
        existing_predicates: list[dict],
    ) -> list[str]:
        """Check if extracted constraints sufficiently cover the description.

        Uses LLM-driven decision instead of fixed thresholds.

        Args:
            item_props: ItemProperties with description
            field_path: Field path
            existing_predicates: Already extracted predicates with metadata

        Returns:
            List of missing constraint descriptions (empty if sufficient)
        """
        description = item_props.description
        if not description or not description.strip():
            return []

        try:
            # Build prompt using centralized builder
            prompt = self.prompt_builder.build_coverage_check_prompt(
                field_path=field_path,
                field_description=description,
                existing_constraints=existing_predicates,
            )

            # Call LLM with lower temperature for consistency
            self.logger.debug(
                "Checking coverage with LLM",
                field_path=field_path,
                existing_count=len(existing_predicates),
            )

            raw_response = await ask(
                prompt=prompt,
                temperature=0.1,
                max_tokens=500,
            )

            # Extract structured output
            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=CoverageCheckResult,
                strict=True,
            )

            # LLM decides sufficiency
            if result.is_sufficient:
                self.logger.debug(
                    "Coverage check: sufficient",
                    field_path=field_path,
                    reasoning=result.reasoning,
                )
                return []

            # Return missing constraints
            if result.missing_constraints:
                self.logger.info(
                    "Coverage check found gaps",
                    field_path=field_path,
                    missing_count=len(result.missing_constraints),
                    reasoning=result.reasoning,
                )
                return result.missing_constraints

            return []

        except LLMError as e:
            self.logger.error(
                "LLM error during coverage check",
                field_path=field_path,
                error=str(e),
            )
            return []  # Best-effort: continue without coverage check
        except Exception as e:
            self.logger.error(
                "Error in coverage check",
                field_path=field_path,
                error=str(e),
                error_type=type(e).__name__,
            )
            return []  # Best-effort: continue without coverage check


__all__ = ["ResPropSingleCoverageChecker"]
