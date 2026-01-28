"""
Predicate prompt builder for LLM extractors.

Dynamically generates LLM prompts with predicate lists from registry,
ensuring single source of truth and eliminating hard-coded predicates.
"""

from typing import List, Dict, Optional
from api_testing.constraint.ir.primitives import get_registry
from api_testing.constraint.ir.primitives.registry_models import PredicateMetadata
from common.logger import get_logger

logger = get_logger(__name__)


class PredicatePromptBuilder:
    """Builder for LLM prompts with dynamic predicate injection.

    Loads predicates from registry and generates formatted prompt text
    for LLM constraint extraction and suggestion tasks.
    All prompts are versioned for tracking changes.
    """

    # Prompt versions for tracking
    COVERAGE_CHECK_PROMPT_V1 = "v1"
    SINGLE_FIELD_EXTRACTION_PROMPT_V1 = "v1"
    CROSS_FIELD_EXTRACTION_PROMPT_V1 = "v1"
    REQUEST_RESPONSE_EXTRACTION_PROMPT_V1 = "v1"

    def __init__(self, include_all: bool = True, category_filter: Optional[str] = None):
        """Initialize prompt builder.

        Args:
            include_all: If True, include all predicates. If False, only implemented ones
            category_filter: Optional category filter (e.g., "integer", "string")
        """
        self.include_all = include_all
        self.category_filter = category_filter
        self.registry = get_registry()
        self._cached_predicate_list: Optional[str] = None

    def build_predicate_list(self, format_style: str = "compact") -> str:
        """Generate formatted list of available predicates.

        Args:
            format_style: "compact" or "detailed"

        Returns:
            Formatted predicate list string for LLM prompt
        """
        if self._cached_predicate_list is not None and format_style == "compact":
            return self._cached_predicate_list

        # Get predicates based on filters
        if self.include_all:
            predicates = self.registry.predicates
        else:
            predicates = self.registry.list_implemented()

        if self.category_filter:
            predicates = [p for p in predicates if p.category == self.category_filter]

        if format_style == "compact":
            result = self._format_compact(predicates)
            if self.include_all and not self.category_filter:
                self._cached_predicate_list = result
            return result
        else:
            return self._format_detailed(predicates)

    def _format_compact(self, predicates: List[PredicateMetadata]) -> str:
        """Format predicates in compact style for prompts.

        Format: "- kind@version: {args_schema}"
        """
        lines = []
        for pred in predicates:
            # Format args schema concisely
            args_display = self._format_args_schema(pred.args_schema.properties)
            lines.append(f"- {pred.kind}@{pred.version}: {args_display}")

        return "\n".join(lines)

    def _format_detailed(self, predicates: List[PredicateMetadata]) -> str:
        """Format predicates with descriptions and examples."""
        lines = []
        for pred in predicates:
            args_display = self._format_args_schema(pred.args_schema.properties)
            lines.append(f"- {pred.kind}@{pred.version}: {args_display}")
            lines.append(f"  Description: {pred.description}")
            if pred.examples:
                example = pred.examples[0]
                lines.append(f"  Example: {example}")

        return "\n".join(lines)

    @staticmethod
    def _format_args_schema(properties: Dict) -> str:
        """Format args schema as compact dict notation."""
        if not properties:
            return "{}"

        parts = []
        for key, schema in properties.items():
            type_str = schema.get("type", "any")
            if schema.get("type") == "array":
                items_type = schema.get("items", {}).get("type", "any")
                type_str = f"[{items_type}, ...]"
            parts.append(f'"{key}": {type_str}')

        return "{" + ", ".join(parts) + "}"

    def get_predicate_list_formatted(self) -> str:
        """Get formatted list of all predicates for prompts.

        Format: Natural language descriptions suitable for LLM understanding.

        Returns:
            Formatted predicate list
        """
        return self.build_predicate_list(format_style="compact")

    def build_coverage_check_prompt(
        self, field_path: str, field_description: str, existing_constraints: List[Dict]
    ) -> str:
        """Build prompt for coverage checker (COVERAGE_CHECK_PROMPT_V1).

        Template: Check if existing constraints cover all requirements in description.

        Args:
            field_path: Field path being analyzed
            field_description: Description text from schema
            existing_constraints: List of existing predicates

        Returns:
            Prompt string with version marker
        """
        # Format existing constraints
        if existing_constraints:
            constraints_str = "\n".join(
                [
                    f"- {c['predicate']['kind']}: {c['predicate']['args']}"
                    for c in existing_constraints
                ]
            )
        else:
            constraints_str = "(none)"

        prompt = f"""You are a validation coverage expert. Analyze if the existing constraints are sufficient.

Field: {field_path}
Description: {field_description}

Existing constraints:
{constraints_str}

Available predicates for reference:
{self.get_predicate_list_formatted()}

Your task: Determine if existing constraints fully cover all validation requirements implied in the description.

Return JSON:
{{
  "is_sufficient": true/false,
  "missing_constraints": ["description of missing constraint 1", "description of missing constraint 2"],
  "reasoning": "Explain what is covered and what is missing"
}}

IMPORTANT:
- missing_constraints should be natural language descriptions, not predicate names
- Only mark as insufficient if there are CLEAR, EXPLICIT requirements not covered
- Empty description or vague description = sufficient
- Prompt version: {self.COVERAGE_CHECK_PROMPT_V1}
"""
        return prompt

    def build_single_field_extraction_prompt(
        self, field_path: str, field_description: str, missing_constraints: List[str]
    ) -> str:
        """Build prompt for single-field LLM extraction (SINGLE_FIELD_EXTRACTION_PROMPT_V1).

        Args:
            field_path: Field path being analyzed
            field_description: Description text from schema
            missing_constraints: List of missing constraint descriptions

        Returns:
            Prompt string with version marker
        """
        missing_str = "\n".join([f"- {m}" for m in missing_constraints])

        prompt = f"""You are a constraint extraction expert. Extract validation predicates for missing constraints.

Field: {field_path}
Description: {field_description}

Missing constraints to extract:
{missing_str}

Available predicates:
{self.get_predicate_list_formatted()}

Return JSON:
{{
  "predicates": [
    {{
      "kind": "predicate_kind",
      "version": "v1",
      "args": {{}},
      "evidence": "quote from description"
    }}
  ]
}}

IMPORTANT:
- Do NOT include @version in the "kind" field
- Use separate "version" field
- If constraint cannot be mapped to existing predicates, return empty list
- Only extract what's explicitly stated
- Prompt version: {self.SINGLE_FIELD_EXTRACTION_PROMPT_V1}
"""
        return prompt

    def build_cross_field_extraction_prompt(
        self, field_pairs: List[tuple], schema_summary: str
    ) -> str:
        """Build prompt for cross-field LLM extraction (CROSS_FIELD_EXTRACTION_PROMPT_V1).

        Args:
            field_pairs: List of (field1, field2) tuples
            schema_summary: Summary of schema structure

        Returns:
            Prompt string with version marker
        """
        pairs_str = "\n".join([f"- {f1} <-> {f2}" for f1, f2 in field_pairs])

        # Filter predicates suitable for cross-field
        cross_field_preds = [
            p
            for p in self.registry.predicates
            if p.category in ["comparison", "date", "number"]
        ]

        lines = []
        for pred in cross_field_preds:
            args_display = self._format_args_schema(pred.args_schema.properties)
            lines.append(f"- {pred.kind}@{pred.version}: {args_display}")

        predicate_list = "\n".join(lines)

        prompt = f"""You are a constraint expert analyzing cross-field relationships in API response schemas.

Schema summary:
{schema_summary}

Potentially related field pairs:
{pairs_str}

Available predicates for cross-field constraints:
{predicate_list}

Return JSON:
{{
  "constraints": [
    {{
      "field1": "path.to.field1",
      "field2": "path.to.field2",
      "predicate_kind": "comparison.lt",
      "predicate_version": "v1",
      "predicate_args": {{}},
      "confidence": 0.0-1.0,
      "evidence": "reasoning"
    }}
  ]
}}

IMPORTANT:
- Only suggest constraints with confidence > 0.7
- Common patterns: startDate < endDate, minValue <= maxValue, createdAt <= updatedAt
- Prompt version: {self.CROSS_FIELD_EXTRACTION_PROMPT_V1}
"""
        return prompt

    def build_extraction_system_prompt(self) -> str:
        """Build system prompt for constraint extraction.

        Returns:
            Complete system prompt with dynamic predicate list
        """
        predicate_list = self.build_predicate_list(format_style="compact")

        prompt = f"""You are a constraint extraction expert. Extract validation predicates from the given constraint descriptions.

Available predicates (use ONLY these):
{predicate_list}

Return JSON:
{{
  "predicates": [
    {{
      "kind": "predicate_kind",
      "version": "v1",
      "args": {{}},
      "evidence": "quote from description"
    }}
  ]
}}

IMPORTANT:
- Do NOT include the version in the "kind" field (e.g., use "int.range" not "int.range@v1")
- The "version" field should be separate (e.g., "v1", "v2")
- If no predicates can be extracted, return {{"predicates": []}}
- Only extract predicates that are explicitly or clearly implied in the constraints
"""
        return prompt

    def build_description_extraction_prompt(self) -> str:
        """Build system prompt for description-based extraction.

        Returns:
            System prompt for description extractor
        """
        predicate_list = self.build_predicate_list(format_style="compact")

        prompt = f"""You are a constraint extraction expert that converts natural language constraint descriptions into structured validation predicates.

Available predicates:
{predicate_list}

Return ONLY valid JSON in this format:
{{
  "predicates": [
    {{"kind": "int.range", "version": "v1", "args": {{"min": 1, "max": 32}}}},
    ...
  ]
}}

IMPORTANT:
- Do NOT include @version suffix in the "kind" field
- Use separate "version" field for version (e.g., "v1")
- If no constraints can be extracted, return {{"predicates": []}}
"""
        return prompt

    def build_suggestion_system_prompt(self) -> str:
        """Build prompt for LLM to suggest NEW predicates.

        Returns:
            System prompt allowing predicate suggestions
        """
        existing_predicates = self.build_predicate_list(format_style="compact")

        prompt = f"""You are a constraint validation expert. The user has a constraint that cannot be expressed with existing predicates.

Existing predicates:
{existing_predicates}

Your task: Design a NEW predicate to express this constraint.

Return JSON:
{{
  "needs_new_predicate": true,
  "proposed_predicate": {{
    "kind": "category.name",
    "version": "v1",
    "category": "integer|string|number|date|boolean|array|object|cross-field",
    "description": "Clear description of what this predicate validates",
    "args_schema": {{
      "type": "object",
      "required": ["arg1"],
      "properties": {{
        "arg1": {{"type": "integer", "description": "..."}}
      }}
    }},
    "reasoning": "Why existing predicates are insufficient"
  }}
}}

Guidelines:
- Keep predicate kind simple and descriptive (e.g., "date.before_field")
- Args schema must follow JSON Schema format
- For cross-field constraints, use category "cross-field"
- Be conservative - only suggest if truly necessary
"""
        return prompt

    def get_predicate_count(self) -> int:
        """Get count of available predicates."""
        if self.include_all:
            predicates = self.registry.predicates
        else:
            predicates = self.registry.list_implemented()

        if self.category_filter:
            predicates = [p for p in predicates if p.category == self.category_filter]

        return len(predicates)

    def build_request_response_prompt(self) -> str:
        """Build system prompt for request-response constraint extraction.

        Returns:
            System prompt for request-response LLM fallback
        """
        # Get predicates suitable for request-response
        comparison_preds = [
            p for p in self.registry.predicates if p.category == "comparison"
        ]
        req_resp_preds = [
            p
            for p in self.registry.predicates
            if "request_response" in p.kind or "forall" in p.kind or "len_" in p.kind
        ]

        combined = comparison_preds + req_resp_preds

        lines = []
        for pred in combined:
            args_display = self._format_args_schema(pred.args_schema.properties)
            lines.append(
                f"- {pred.kind}@{pred.version}: {args_display} - {pred.description[:80]}"
            )

        predicate_list = "\n".join(lines)

        prompt = f"""You are an API constraint expert analyzing request-response relationships.

Given request parameters and response schema, identify validation constraints where:
- Request parameter values constrain or match response field values
- Response arrays are filtered/limited by request parameters
- Response data is sorted/ordered by request parameters

Common patterns:
1. Echo/Identity: path param {{id}} matches response.id (use: comparison.equals@v1)
2. Filter: query param status=X → all items have status=X (use: forall_eq@v1)
3. Pagination: query param limit=N → array length <= N (use: len_le@v1)
4. Sort: query param sort=field → array sorted by field (use: sorted_by@v1)
5. Range: startDate/endDate filter date fields (use: date_in_range@v1)

Available predicates:
{predicate_list}

Return JSON:
{{
  "relationships": [
    {{
      "request_selector": "$request.path.id" or "$request.query.status",
      "response_selector": "$response.body$.id" or "$response.body$.items[*].status",
      "predicate_kind": "comparison.equals",
      "predicate_version": "v1",
      "predicate_args": {{}},
      "confidence": 0.0-1.0,
      "evidence": "reasoning why this relationship exists"
    }}
  ]
}}

IMPORTANT:
- Only suggest relationships with confidence > 0.7
- Use $request.path.<name>, $request.query.<name>, $request.header.<name> for request refs
- Use $response.body$.<path> for JSONPath response refs
- Do NOT include @version in "predicate_kind" field
"""
        return prompt

    def build_request_response_categorized_prompt(self) -> str:
        """Build system prompt with predicates organized by category.

        Returns:
            System prompt with predicates grouped for better readability
        """
        # Organize predicates by use case
        categories = {
            "Comparison (Echo/Identity)": [],
            "Array Operations (Filter/Sort)": [],
            "Conditional (Projection)": [],
        }

        for pred in self.registry.predicates:
            if pred.category == "comparison":
                categories["Comparison (Echo/Identity)"].append(pred)
            elif any(kw in pred.kind for kw in ["forall", "sorted", "len_"]):
                categories["Array Operations (Filter/Sort)"].append(pred)
            elif any(kw in pred.kind for kw in ["implies", "field_exists"]):
                categories["Conditional (Projection)"].append(pred)

        sections = []
        for category, preds in categories.items():
            if not preds:
                continue

            lines = [f"## {category}"]
            for pred in preds:
                args_display = self._format_args_schema(pred.args_schema.properties)
                lines.append(f"- {pred.kind}@{pred.version}: {args_display}")
                if pred.description:
                    lines.append(f"  → {pred.description[:100]}")

            sections.append("\n".join(lines))

        predicate_list = "\n\n".join(sections)

        prompt = f"""You are an API constraint expert analyzing request-response relationships.

Available predicates organized by use case:

{predicate_list}

Identify constraints where request parameters affect or match response data.

Return JSON with detected relationships. Only include high-confidence matches (>0.7).
"""
        return prompt


__all__ = ["PredicatePromptBuilder"]
