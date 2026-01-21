"""
Coverage checker for cross-field constraints.

Uses LLM to determine if heuristic extraction is complete or if
additional relationships exist that weren't detected.
"""

from typing import List, Dict
from pydantic import BaseModel

from api_testing.models.specification_model import ItemProperties
from api_testing.constraint.extractors.common import CandidateConstraint
from common.logger import get_logger
from common.llm import ask
from common.llm.extractors import StructuredOutputExtractor
from common.llm.exceptions import LLMError

logger = get_logger(__name__)


class MissingRelationship(BaseModel):
    """A missing cross-field relationship."""

    field_a: str
    field_b: str
    relationship_description: str
    confidence: str  # "high", "medium", "low"


class CrossFieldCoverageOutput(BaseModel):
    """LLM output for cross-field coverage check."""

    is_complete: bool
    missing_relationships: List[MissingRelationship] = []


CROSSFIELD_COVERAGE_SYSTEM_PROMPT = """You are a constraint completeness checker for API response schemas.

Given:
1. A response schema with multiple fields
2. Already detected cross-field relationships (from heuristic extraction)

Determine:
- Are there additional field relationships that should be validated?
- Is the coverage complete or are relationships missing?

Common relationships to check:
- Date/time comparisons (start < end, created < updated)
- Numeric comparisons (min < max, price > discountedPrice)
- Dependent fields (if field A exists, field B must exist)
- Consistency constraints (fields that must match)

Return JSON:
{
  "is_complete": true|false,
  "missing_relationships": [
    {
      "field_a": "fieldName1",
      "field_b": "fieldName2",
      "relationship_description": "Brief description of the relationship",
      "confidence": "high|medium|low"
    }
  ]
}

Guidelines:
- Only report relationships that are semantically clear from field names/types
- Don't infer complex business logic
- Mark is_complete=true if all obvious relationships are detected
- Return empty array if no relationships are missing
"""


CROSSFIELD_COVERAGE_USER_PROMPT = """Check if cross-field relationship detection is complete.

Response Schema Fields:
{schema_description}

Already Detected Relationships:
{detected_relationships}

Are there any additional field relationships that should be validated?"""


class ResPropCrossFieldCoverageChecker:
    """Check if heuristic cross-field extraction is complete.

    Uses LLM to identify missing relationships that heuristics didn't catch.
    """

    def __init__(self):
        """Initialize coverage checker."""
        self.logger = logger

    async def check(
        self,
        response_schema: ItemProperties,
        heuristic_results: List[CandidateConstraint],
    ) -> List[MissingRelationship]:
        """Check coverage of heuristic extraction.

        Args:
            response_schema: Response schema
            heuristic_results: Candidates from heuristic extraction

        Returns:
            List of missing relationships (empty if complete)
        """
        if not response_schema or not response_schema.properties:
            return []

        # Flatten schema for description
        flattened = self._flatten_schema(response_schema)

        if len(flattened) < 2:
            # Need at least 2 fields for relationships
            return []

        try:
            # Build schema description
            schema_desc = self._build_schema_description(flattened)

            # Build detected relationships description
            detected_desc = self._build_detected_description(heuristic_results)

            # Build prompt
            prompt = CROSSFIELD_COVERAGE_USER_PROMPT.format(
                schema_description=schema_desc,
                detected_relationships=detected_desc or "None detected yet",
            )

            self.logger.debug(
                "Checking cross-field coverage with LLM",
                detected_count=len(heuristic_results),
            )

            # Call LLM
            raw_response = await ask(
                prompt=prompt,
                system=CROSSFIELD_COVERAGE_SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=800,
            )

            # Extract structured output
            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=CrossFieldCoverageOutput,
                strict=True,
            )

            if result.is_complete:
                self.logger.info("Cross-field coverage is complete")
                return []

            if result.missing_relationships:
                self.logger.info(
                    f"Found {len(result.missing_relationships)} missing cross-field relationships"
                )
                return result.missing_relationships

            return []

        except LLMError as e:
            self.logger.error(
                "LLM error during coverage check",
                error=str(e),
            )
            return []
        except Exception as e:
            self.logger.error(
                "Error in coverage check",
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

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
            }

            # Recursively flatten nested objects (but not arrays)
            if field_schema.type == "object" and field_schema.properties:
                nested = self._flatten_schema(field_schema, field_path)
                result.update(nested)

        return result

    def _build_schema_description(self, flattened: Dict[str, Dict]) -> str:
        """Build readable schema description for LLM.

        Args:
            flattened: Flattened field mapping

        Returns:
            Formatted schema description
        """
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

    def _build_detected_description(
        self,
        candidates: List[CandidateConstraint],
    ) -> str:
        """Build description of detected relationships.

        Args:
            candidates: Detected candidates

        Returns:
            Formatted description
        """
        if not candidates:
            return ""

        lines = []
        for i, candidate in enumerate(candidates, 1):
            # Extract field names from selectors
            fields = []
            for selector in candidate.selectors:
                if "$response.body$." in selector:
                    field = selector.split("$response.body$.")[-1]
                    fields.append(field)

            if len(fields) >= 2:
                lines.append(
                    f"{i}. {fields[0]} {candidate.predicate_kind.split('.')[-1]} {fields[1]}"
                )

        return "\n".join(lines) if lines else ""


__all__ = ["ResPropCrossFieldCoverageChecker", "MissingRelationship"]
