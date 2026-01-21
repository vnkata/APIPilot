"""
LLM-based cross-field constraint extractor.

Extracts cross-field relationships that heuristics couldn't detect,
with predicate mapping and suggestion support.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel

from api_testing.models.specification_model import ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from api_testing.constraint.extractors.prompt_builder import PredicatePromptBuilder
from api_testing.constraint.primitives.registry_loader import (
    get_predicate,
    validate_predicate_args,
    ProposedPredicateManager,
)
from api_testing.constraint.extractors.response_property.multi.coverage_checker import (
    MissingRelationship,
)
from common.logger import get_logger
from common.llm import ask
from common.llm.extractors import StructuredOutputExtractor
from common.llm.exceptions import LLMError

logger = get_logger(__name__)


class ResPropCrossFieldPredicateOutput(BaseModel):
    """Single cross-field predicate from LLM."""

    field_a: str
    field_b: str
    kind: str
    version: str = "v1"
    args: Dict = {}
    evidence: str


class ResPropCrossFieldExtractionOutput(BaseModel):
    """LLM output for cross-field extraction."""

    predicates: List[ResPropCrossFieldPredicateOutput] = []


class ResPropCrossFieldSuggestionOutput(BaseModel):
    """LLM output for predicate suggestion."""

    needs_new_predicate: bool
    proposed_predicate: Optional[Dict] = None
    reasoning: Optional[str] = None


RES_PROP_CROSSFIELD_EXTRACTION_USER_PROMPT = """Extract cross-field constraints for the following missing relationships.

Response Schema Fields:
{schema_description}

Missing Relationships to Extract:
{missing_relationships}

For each relationship, identify:
1. The appropriate predicate from the available list
2. The exact field names (field_a, field_b)
3. Any required arguments

Return JSON with predicates array."""


class ResPropCrossFieldLLMExtractor:
    """LLM-based extractor for cross-field constraints.

    Handles relationships that heuristics couldn't detect,
    with predicate mapping and suggestion support.
    """

    def __init__(self, allow_suggestions: bool = True):
        """Initialize LLM extractor.

        Args:
            allow_suggestions: Whether to allow predicate suggestions
        """
        self.logger = logger
        self.allow_suggestions = allow_suggestions
        self.prompt_builder = PredicatePromptBuilder(include_all=True)
        self._system_prompt = self._build_system_prompt()
        self._suggestion_prompt = self.prompt_builder.build_suggestion_system_prompt()
        self.proposal_manager = (
            ProposedPredicateManager() if allow_suggestions else None
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt with available predicates.

        Returns:
            System prompt string
        """
        predicate_list = self.prompt_builder.build_predicate_list(
            format_style="compact"
        )

        prompt = f"""You are a cross-field constraint expert for API responses.

Available predicates for cross-field constraints:
{predicate_list}

Your task: Extract cross-field constraints using ONLY the predicates listed above.

Guidelines:
- Use comparison predicates for date/numeric relationships
- For complex relationships, choose the closest matching predicate
- If no predicate fits, return empty array (suggestion will be handled separately)
- Ensure field names exactly match the schema

Return JSON:
{{
  "predicates": [
    {{
      "field_a": "fieldName1",
      "field_b": "fieldName2",
      "kind": "comparison.less_than_or_equal",
      "version": "v1",
      "args": {{}},
      "evidence": "Brief explanation"
    }}
  ]
}}
"""
        return prompt

    async def extract(
        self,
        response_schema: ItemProperties,
        missing_relationships: List[MissingRelationship],
        operation_id: Optional[str] = None,
    ) -> List[CandidateConstraint]:
        """Extract cross-field constraints for missing relationships.

        Args:
            response_schema: Response schema
            missing_relationships: Relationships to extract
            operation_id: Operation ID

        Returns:
            List of candidate constraints
        """
        if not missing_relationships:
            return []

        candidates = []

        # Flatten schema
        flattened = self._flatten_schema(response_schema)

        try:
            # Build schema description
            schema_desc = self._build_schema_description(flattened)

            # Build missing relationships description
            missing_desc = self._build_missing_description(missing_relationships)

            # Build prompt
            prompt = RES_PROP_CROSSFIELD_EXTRACTION_USER_PROMPT.format(
                schema_description=schema_desc,
                missing_relationships=missing_desc,
            )

            self.logger.debug(
                "Extracting cross-field constraints with LLM",
                missing_count=len(missing_relationships),
            )

            # Call LLM
            raw_response = await ask(
                prompt=prompt,
                system=self._system_prompt,
                temperature=0.1,
                max_tokens=1000,
            )

            # Extract structured output
            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=ResPropCrossFieldExtractionOutput,
                strict=True,
            )

            # Convert to candidates
            for llm_pred in result.predicates:
                # Normalize kind
                kind = llm_pred.kind
                if "@v" in kind:
                    kind, _ = kind.split("@", 1)

                # Validate predicate exists
                meta = get_predicate(kind, llm_pred.version)
                if not meta:
                    self.logger.warning(
                        "LLM returned unknown predicate",
                        predicate=f"{kind}@{llm_pred.version}",
                    )

                    # Try to suggest new predicate
                    if self.allow_suggestions:
                        await self._suggest_new_predicate(
                            llm_pred.field_a,
                            llm_pred.field_b,
                            llm_pred.evidence,
                            flattened,
                        )
                    continue

                # Validate args
                if not validate_predicate_args(kind, llm_pred.version, llm_pred.args):
                    self.logger.warning(
                        "LLM returned invalid args",
                        predicate=f"{kind}@{llm_pred.version}",
                        args=llm_pred.args,
                    )
                    continue

                # Create candidate
                candidate = self._create_candidate(
                    llm_pred.field_a,
                    llm_pred.field_b,
                    kind,
                    llm_pred.version,
                    llm_pred.args,
                    llm_pred.evidence,
                    operation_id,
                )
                candidates.append(candidate)

            if candidates:
                self.logger.info(
                    f"LLM cross-field extraction successful: {len(candidates)} constraints"
                )

        except LLMError as e:
            self.logger.error(
                "LLM error during cross-field extraction",
                error=str(e),
            )
        except Exception as e:
            self.logger.error(
                "Error in cross-field LLM extraction",
                error=str(e),
                error_type=type(e).__name__,
            )

        return candidates

    def _flatten_schema(
        self,
        schema: ItemProperties,
        prefix: str = "",
    ) -> Dict[str, Dict]:
        """Flatten schema into field_path -> field_info mapping."""
        result = {}

        if not schema or not schema.properties:
            return result

        for field_name, field_schema in schema.properties.items():
            field_path = f"{prefix}.{field_name}" if prefix else field_name

            result[field_path] = {
                "type": field_schema.type,
                "format": field_schema.format,
                "description": field_schema.description or "",
            }

            if field_schema.type == "object" and field_schema.properties:
                nested = self._flatten_schema(field_schema, field_path)
                result.update(nested)

        return result

    def _build_schema_description(self, flattened: Dict[str, Dict]) -> str:
        """Build readable schema description for LLM."""
        lines = []

        for field_path, field_info in flattened.items():
            field_type = field_info.get("type", "unknown")
            field_format = field_info.get("format")
            field_desc = field_info.get("description", "")

            type_str = field_type
            if field_format:
                type_str = f"{field_type} (format: {field_format})"

            line = f"- {field_path}: {type_str}"
            if field_desc:
                line += f" - {field_desc[:80]}"

            lines.append(line)

        return "\n".join(lines)

    def _build_missing_description(
        self,
        missing: List[MissingRelationship],
    ) -> str:
        """Build description of missing relationships."""
        lines = []

        for i, rel in enumerate(missing, 1):
            lines.append(
                f"{i}. {rel.field_a} ↔ {rel.field_b}: {rel.relationship_description} "
                f"(confidence: {rel.confidence})"
            )

        return "\n".join(lines)

    def _create_candidate(
        self,
        field_a: str,
        field_b: str,
        kind: str,
        version: str,
        args: Dict,
        evidence: str,
        operation_id: Optional[str],
    ) -> CandidateConstraint:
        """Create a candidate constraint."""
        candidate = CandidateConstraint(
            predicate_kind=kind,
            predicate_version=version,
            predicate_args=args,
            selectors=[
                f"$response.body$.{field_a}",
                f"$response.body$.{field_b}",
            ],
            selector_types=["jsonpath", "jsonpath"],
            operation_id=operation_id or "unknown",
            phase="response",
            location="body",
            confidence=0.7,  # Lower confidence for LLM
            tags=["cross_field", "llm"],
            extractor_name="CrossFieldLLMExtractor",
        )

        candidate.add_evidence(
            source="llm",
            location=f"response.{field_a},{field_b}",
            snippet=evidence,
            confidence=0.7,
        )

        return candidate

    async def _suggest_new_predicate(
        self,
        field_a: str,
        field_b: str,
        evidence: str,
        flattened: Dict[str, Dict],
    ) -> None:
        """Suggest a new predicate for unmappable constraint.

        Args:
            field_a: First field name
            field_b: Second field name
            evidence: Evidence string
            flattened: Flattened schema
        """
        if not self.proposal_manager:
            return

        try:
            # Get field types
            field_a_info = flattened.get(field_a, {})
            field_b_info = flattened.get(field_b, {})

            prompt = f"""Cannot express cross-field constraint with existing predicates.

Field A: {field_a} (type: {field_a_info.get('type', 'unknown')})
Field B: {field_b} (type: {field_b_info.get('type', 'unknown')})
Relationship: {evidence}

Design a new predicate to express this cross-field constraint."""

            self.logger.debug(
                "Asking LLM to suggest new cross-field predicate",
                field_a=field_a,
                field_b=field_b,
            )

            raw_response = await ask(
                prompt=prompt,
                system=self._suggestion_prompt,
                temperature=0.2,
                max_tokens=600,
            )

            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=ResPropCrossFieldSuggestionOutput,
                strict=True,
            )

            if result.needs_new_predicate and result.proposed_predicate:
                pred = result.proposed_predicate

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
                    success = self.proposal_manager.add_proposal(
                        kind=pred["kind"],
                        version=pred.get("version", "v1"),
                        category=pred["category"],
                        description=pred["description"],
                        args_schema=pred["args_schema"],
                        evidence=result.reasoning or evidence,
                        field_context=f"{field_a},{field_b}",
                        proposed_by="llm",
                    )

                    if success:
                        self.logger.info(
                            "LLM suggested new cross-field predicate",
                            predicate=f"{pred['kind']}@{pred.get('version', 'v1')}",
                            fields=f"{field_a},{field_b}",
                        )

        except LLMError as e:
            self.logger.error(
                "LLM error during predicate suggestion",
                error=str(e),
            )
        except Exception as e:
            self.logger.error(
                "Error in predicate suggestion",
                error=str(e),
                error_type=type(e).__name__,
            )


__all__ = ["ResPropCrossFieldLLMExtractor"]
