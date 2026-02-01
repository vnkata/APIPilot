"""
LLM-based extractor for request-response constraints.

Handles unmatched parameters that heuristics couldn't process,
with predicate mapping and suggestion support.
"""

from pydantic import BaseModel

from api_testing.constraint.ir.core.parameter_model import ParameterInfo
from api_testing.constraint.ir.extractors.common import CandidateConstraint
from api_testing.constraint.ir.extractors.prompt_builder import PredicatePromptBuilder
from api_testing.constraint.ir.primitives import (
    ProposedPredicateManager,
    get_predicate,
    validate_predicate_args,
)
from api_testing.models.specification_model import OperationProperties
from common.llm import ask
from common.llm.exceptions import LLMError
from common.llm.extractors import StructuredOutputExtractor
from common.logger import get_logger

logger = get_logger(__name__)


class RequestResponsePredicateOutput(BaseModel):
    """Single request-response predicate from LLM."""

    parameter_name: str
    response_field: str
    kind: str
    version: str = "v1"
    args: dict = {}
    evidence: str
    confidence: float = 0.7


class RequestResponseExtractionOutput(BaseModel):
    """LLM output for request-response extraction."""

    predicates: list[RequestResponsePredicateOutput] = []


class RequestResponseSuggestionOutput(BaseModel):
    """LLM output for predicate suggestion."""

    needs_new_predicate: bool
    proposed_predicate: dict | None = None
    reasoning: str | None = None


REQRESP_EXTRACTION_USER_PROMPT = """Analyze unmatched request parameters and determine if they affect the response.

Operation: {operation_id} ({method})
Endpoint: {path}

Unmatched Parameters:
{parameters_description}

Response Schema:
{response_schema}

For each parameter, determine:
1. Does it affect the response data? (filter, sort, pagination, search, etc.)
2. Which response field(s) does it affect?
3. What predicate best describes the relationship?

Return JSON with predicates array. Only include parameters that clearly affect the response."""


class RequestResponseLLMExtractor:
    """LLM-based extractor for unmatched request parameters.

    Analyzes parameters that heuristics couldn't match and determines
    if they have request-response constraints.
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
        predicate_list = self.prompt_builder.build_request_response_categorized_prompt()

        prompt = f"""You are a request-response constraint expert for APIs.

{predicate_list}

Your task: Identify constraints where request parameters affect response data.

Common patterns:
- Echo/Identity: Parameter value appears in response (comparison.equals)
- Filter: Parameter filters array items (forall_eq)
- Pagination: Parameter limits response size (len_le, len_eq)
- Sort: Parameter controls response ordering (sorted_by)
- Search: Parameter matches response content (contains_substring)
- Range: Parameter constrains response values (date_in_range, between)
- Projection: Parameter controls field presence (field_exists, field_absent, implies)

Guidelines:
- Only extract if relationship is clear from parameter name/description
- Use the most specific predicate available
- If no predicate fits, return empty array (suggestion handled separately)
- Ensure parameter and field names exactly match

Return JSON:
{{
  "predicates": [
    {{
      "parameter_name": "userId",
      "response_field": "user.id",
      "kind": "comparison.equals",
      "version": "v1",
      "args": {{}},
      "evidence": "Brief explanation",
      "confidence": 0.8
    }}
  ]
}}
"""
        return prompt

    async def extract(
        self,
        operation: OperationProperties,
        unmatched_params: list[ParameterInfo],
    ) -> list[CandidateConstraint]:
        """Extract request-response constraints for unmatched parameters.

        Args:
            operation: Operation properties
            unmatched_params: Parameters not matched by heuristics

        Returns:
            List of candidate constraints
        """
        if not unmatched_params:
            return []

        candidates = []

        try:
            # Get response schema
            response_schema = operation.get_success_response_schema()

            if not response_schema:
                self.logger.debug(
                    "No response schema available for LLM extraction",
                    operation=operation.uuid,
                )
                return []

            # Build descriptions
            params_desc = self._build_parameters_description(unmatched_params)
            response_desc = self._build_response_description(response_schema)

            # Build prompt
            prompt = REQRESP_EXTRACTION_USER_PROMPT.format(
                operation_id=operation.operation_id or "unknown",
                method=operation.method or "unknown",
                path=operation.path or "unknown",
                parameters_description=params_desc,
                response_schema=response_desc,
            )

            self.logger.debug(
                "Extracting request-response constraints with LLM",
                operation=operation.uuid,
                unmatched_count=len(unmatched_params),
            )

            # Call LLM
            raw_response = await ask(
                prompt=prompt,
                system=self._system_prompt,
                temperature=0.1,
                max_tokens=1200,
            )

            # Extract structured output
            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=RequestResponseExtractionOutput,
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
                        operation=operation.uuid,
                    )

                    # Try to suggest new predicate
                    if self.allow_suggestions:
                        await self._suggest_new_predicate(
                            llm_pred.parameter_name,
                            llm_pred.response_field,
                            llm_pred.evidence,
                            operation,
                        )
                    continue

                # Validate args
                if not validate_predicate_args(kind, llm_pred.version, llm_pred.args):
                    self.logger.warning(
                        "LLM returned invalid args",
                        predicate=f"{kind}@{llm_pred.version}",
                        args=llm_pred.args,
                        operation=operation.uuid,
                    )
                    continue

                # Find parameter info
                param_info = next(
                    (p for p in unmatched_params if p.name == llm_pred.parameter_name),
                    None,
                )

                if not param_info:
                    self.logger.warning(
                        "LLM returned unknown parameter",
                        parameter=llm_pred.parameter_name,
                        operation=operation.uuid,
                    )
                    continue

                # Create candidate
                candidate = self._create_candidate(
                    param_info,
                    llm_pred.response_field,
                    kind,
                    llm_pred.version,
                    llm_pred.args,
                    llm_pred.evidence,
                    llm_pred.confidence,
                    operation.uuid,
                )
                candidates.append(candidate)

            if candidates:
                self.logger.info(
                    f"LLM request-response extraction successful: {len(candidates)} constraints",
                    operation=operation.uuid,
                )

        except LLMError as e:
            self.logger.error(
                "LLM error during request-response extraction",
                operation=operation.uuid,
                error=str(e),
            )
        except Exception as e:
            self.logger.error(
                "Error in request-response LLM extraction",
                operation=operation.uuid,
                error=str(e),
                error_type=type(e).__name__,
            )

        return candidates

    @staticmethod
    def _build_parameters_description(
        params: list[ParameterInfo],
    ) -> str:
        """Build readable parameters description for LLM.

        Args:
            params: List of parameters

        Returns:
            Formatted description
        """
        lines = []

        for param in params:
            type_str = param.schema_type or "unknown"
            if param.format:
                type_str = f"{type_str} (format: {param.format})"

            line = f"- {param.name} ({param.location}): {type_str}"
            if param.required:
                line += " [required]"
            if param.description:
                line += f" - {param.description[:100]}"

            lines.append(line)

        return "\n".join(lines)

    def _build_response_description(
        self,
        schema: dict,
    ) -> str:
        """Build readable response schema description for LLM.

        Args:
            schema: Response schema

        Returns:
            Formatted description
        """
        # Flatten schema
        flattened = self._flatten_schema(schema)

        lines = []
        for field_path, field_info in flattened.items():
            field_type = field_info.get("type", "unknown")
            field_format = field_info.get("format")

            type_str = field_type
            if field_format:
                type_str = f"{field_type} (format: {field_format})"

            line = f"- {field_path}: {type_str}"

            lines.append(line)

        return "\n".join(lines[:50])  # Limit to 50 fields to avoid token limit

    def _flatten_schema(
        self,
        schema: dict,
        prefix: str = "",
    ) -> dict[str, dict]:
        """Flatten schema into field_path -> field_info mapping.

        Args:
            schema: Schema to flatten
            prefix: Path prefix

        Returns:
            Dict of field_path -> field_info
        """
        result = {}

        if not isinstance(schema, dict):
            return result

        properties = schema.get("properties", {})

        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue

            field_path = f"{prefix}.{field_name}" if prefix else field_name

            result[field_path] = {
                "type": field_schema.get("type", "unknown"),
                "format": field_schema.get("format"),
            }

            # Recursively flatten nested objects
            if field_schema.get("type") == "object" and "properties" in field_schema:
                nested = self._flatten_schema(field_schema, field_path)
                result.update(nested)

        return result

    @staticmethod
    def _create_candidate(
        param: ParameterInfo,
        response_field: str,
        kind: str,
        version: str,
        args: dict,
        evidence: str,
        confidence: float,
        operation_id: str,
    ) -> CandidateConstraint:
        """Create a candidate constraint.

        Args:
            param: Parameter info
            response_field: Response field path
            kind: Predicate kind
            version: Predicate version
            args: Predicate args
            evidence: Evidence string
            confidence: Confidence score
            operation_id: Operation ID

        Returns:
            CandidateConstraint
        """
        # Build selectors
        request_selector = f"$request.{param.location}$.{param.name}"
        response_selector = f"$response.body$.{response_field}"

        candidate = CandidateConstraint(
            predicate_kind=kind,
            predicate_version=version,
            predicate_args=args,
            selectors=[request_selector, response_selector],
            selector_types=["request_ref", "jsonpath"],
            operation_id=operation_id,
            phase="response",
            location="body",
            confidence=confidence,
            tags=["request_response", "llm"],
            extractor_name="RequestResponseLLMExtractor",
        )

        candidate.add_evidence(
            source="llm",
            location=f"request.{param.name} -> response.{response_field}",
            snippet=evidence,
            confidence=confidence,
        )

        return candidate

    async def _suggest_new_predicate(
        self,
        param_name: str,
        response_field: str,
        evidence: str,
        operation: OperationProperties,
    ) -> None:
        """Suggest a new predicate for unmappable constraint.

        Args:
            param_name: Parameter name
            response_field: Response field path
            evidence: Evidence string
            operation: Operation properties
        """
        if not self.proposal_manager:
            return

        try:
            prompt = f"""Cannot express request-response constraint with existing predicates.

Operation: {operation.operation_id} ({operation.method})
Request Parameter: {param_name}
Response Field: {response_field}
Relationship: {evidence}

Design a new predicate to express this request-response constraint."""

            self.logger.debug(
                "Asking LLM to suggest new request-response predicate",
                parameter=param_name,
                field=response_field,
                operation=operation.uuid,
            )

            raw_response = await ask(
                prompt=prompt,
                system=self._suggestion_prompt,
                temperature=0.2,
                max_tokens=600,
            )

            result = StructuredOutputExtractor.extract(
                raw_text=raw_response,
                model_class=RequestResponseSuggestionOutput,
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
                        field_context=f"{param_name} -> {response_field}",
                        proposed_by="llm",
                    )

                    if success:
                        self.logger.info(
                            "LLM suggested new request-response predicate",
                            predicate=f"{pred['kind']}@{pred.get('version', 'v1')}",
                            parameter=param_name,
                            field=response_field,
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


__all__ = ["RequestResponseLLMExtractor"]
