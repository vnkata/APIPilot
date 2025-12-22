"""
Response constraints extraction prompt class.

Extracts constraints, rules, and limitations from response schema attributes
using LLM with structured outputs.
"""

import asyncio
import json
import re
from typing import Optional
from common.llm import ask
from common.llm.exceptions import LLMError, LLMValidationError
from common.logger import get_logger, LogLevel
from api_testing.prompts.response_constraints.schema import (
    ResponsePropertyConstraintsOutput,
)
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("response_constraints", level=LogLevel.DEBUG)

RESPONSE_PROPERTY_CONSTRAINTS_MINING_SYSTEM_PROMPT_V1 = """
You are given a schema and its attributes. Identify any constraints, rules, or limitations implied by each attribute’s description. Confirm that the description contains enough information to support automated validation of these constraints.
Follow these steps below to complete your task:
**STEP 1**: Review the provided schema and its attributes. Briefly describe the purpose or function of each attribute based on its definition or description.
**STEP 2**: From STEP 1, identify attributes whose name and descriptions imply constraints, rules, or limits that can be programmatically verified:
- Semantic inference: Constraints can be inferred from the attribute’s name and description based on their common or contextual meaning.
- General: Descriptions defining specific values, ranges, formats, or logic indicate constraints.
- Format: Mention or imply URI/URL, timestamp (ISO 8601), email, slug, date, datetime, version, or schema hints like format: uri, format: date-time.
- Enum: Fixed value sets (e.g., “one of public, private”).
- Range: Numeric or string limits (e.g., “≤255”, “1–10”, “max length 32”).
- Ignore vague terms: “recommended”, “typically”, “usually” are not constraints unless precise.
- Examples: Examples showing valid formats (URL, date, etc.) imply constraints if consistent.

FINAL OUTPUT:
The response is in the format below, no explanation is needed:
```json {
  "constraints": {
    "attribute_name_1": "briefly_description_1",
    "attribute_name_2": "briefly_description_2",
  }
}
```
"""

RESPONSE_PROPERTY_CONSTRAINTS_MINING_USER_PROMPT_V1 = """
Please review the following details for the schema and its attributes:
Schema: {schema}
Attributes:
{attributes}
"""

RESPONSE_PROPERTY_CONSTRAINTS_MINING_SYSTEM_PROMPT_V2 = """You are given a schema and its attributes. Identify any constraints, rules, or limitations implied by each attribute's description. Confirm that the description contains enough information to support automated validation of these constraints.
Follow these steps below to complete your task:
**STEP 1**: Review the provided schema and its attributes. Briefly describe the purpose or function of each attribute based on its definition or description.
**STEP 2**: From STEP 1, identify attributes whose name and descriptions imply constraints, rules, or limits that can be programmatically verified:
- Semantic inference: Constraints can be inferred from the attribute's name and description based on their common or contextual meaning.
- General: Descriptions defining specific values, ranges, formats, or logic indicate constraints.
- Format: Mention or imply URI/URL, timestamp (ISO 8601), email, slug, date, datetime, version, or schema hints like format: uri, format: date-time.
- Enum: Fixed value sets (e.g., "one of public, private").
- Range: Numeric or string limits (e.g., "≤255", "1–10", "max length 32").
- Ignore vague terms: "recommended", "typically", "usually" are not constraints unless precise.
- Examples: Examples showing valid formats (URL, date, etc.) imply constraints if consistent.

FINAL OUTPUT:
Return a JSON object with a "constraints" field mapping attribute names to their constraint descriptions."""


RESPONSE_PROPERTY_CONSTRAINTS_MINING_USER_PROMPT_V2 = """Please review the following details for the schema and its attributes:
Schema: {schema}
Attributes:
{attributes}"""

RESPONSE_PROPERTY_CONSTRAINTS_MINING_SYSTEM_PROMPT_V3 = """You are an expert at analyzing API schema attributes and extracting programmatically verifiable constraints.

Your task is to identify constraints, rules, or limitations implied by each attribute's description that can be used for automated validation.

**Analysis Guidelines:**
1. Review each attribute's name, type, format, and description
2. Identify constraints that can be programmatically verified:
   - **Format constraints**: ISO 8601 dates, URIs, emails, specific formats
   - **Range constraints**: Numeric min/max, string length limits
   - **Enum constraints**: Fixed value sets (e.g., [1, 0], ["public", "private"])
   - **Semantic constraints**: Inferred from attribute names and descriptions (e.g., "id" implies positive integer, "date" implies valid date format)
   - **Type-specific constraints**: minimum/maximum for numbers, minLength/maxLength for strings

3. **Ignore vague terms** unless they specify precise limits:
   - Skip: "recommended", "typically", "usually", "may", "can"
   - Include: Specific ranges, formats, enums, or clear semantic meanings

4. **Extract constraint descriptions** that are:
   - Concise but specific (e.g., "Integer between 1 and 32", "ISO date format (YYYY-MM-DD)", "Must be 1 or 0")
   - Actionable for validation logic
   - Based on explicit schema properties (minimum, maximum, format, enum) or clear semantic inference

**Important**: You must extract constraints for ALL attributes that have verifiable constraints. Do not return an empty constraints dictionary unless truly no constraints can be identified."""


class ResponsePropertyConstraintMiner:
    """Extracts constraints from response schema attributes using LLM.

    This class uses structured LLM outputs to identify constraints,
    rules, and limitations implied by schema attribute descriptions.

    Features:
    - Structured output via Pydantic validation (primary method)
    - Fallback to raw output parsing if structured output fails or returns empty
    - Automatic retry with improved prompts
    - Validation to ensure non-empty constraints when attributes are provided

    Example:
        >>> from api_testing.prompts.response_constraints import ResponsePropertyConstraintMiner
        >>> extractor = ResponsePropertyConstraintMiner()
        >>> result = await extractor.extract_response_property_constraints(
        ...     schema="User",
        ...     attributes="- name: a string attribute..."
        ... )
        >>> print(result.constraints)
    """

    SYSTEM_PROMPT: str = RESPONSE_PROPERTY_CONSTRAINTS_MINING_SYSTEM_PROMPT_V3
    USER_PROMPT: str = RESPONSE_PROPERTY_CONSTRAINTS_MINING_USER_PROMPT_V1
    MAX_RETRIES: int = 2  # Retry once with fallback parsing

    def __init__(self, llm: Optional[object] = None) -> None:
        """Initialize ResponseConstraints extractor.

        Args:
            llm: Deprecated parameter (kept for backward compatibility).
                The class now uses src/common/llm directly.
        """

    def _parse_json_from_text(self, text: str) -> Optional[dict]:
        """Extract JSON from text that may contain markdown code blocks.

        Args:
            text: Text that may contain JSON in code blocks or plain JSON

        Returns:
            Parsed dict or None if parsing fails
        """
        # Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try to find JSON object directly
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    async def _extract_with_fallback(
        self, prompt: str, schema: str, attributes: str
    ) -> ResponsePropertyConstraintsOutput:
        """Extract constraints with fallback to raw output parsing.

        Args:
            prompt: User prompt
            schema: Schema name for logging
            attributes: Original attributes string for validation

        Returns:
            ResponsePropertyConstraintsOutput

        Raises:
            LLMError: If all extraction methods fail
        """
        # Primary: Try structured output
        try:
            logger.debug(
                f"Attempting structured output extraction for schema: {schema}"
            )
            result = await ask(
                prompt=prompt,
                system=self.SYSTEM_PROMPT,
                response_model=ResponsePropertyConstraintsOutput,
                temperature=0.3,
            )

            # Validate that constraints were actually extracted
            if result.constraints:
                logger.debug(
                    f"Structured output successful: schema={schema}, "
                    f"constraints_count={len(result.constraints)}"
                )
                return result
            else:
                # Count attributes to determine if empty result is expected
                attribute_count = attributes.count("- ")
                if attribute_count > 0:
                    logger.warning(
                        f"Structured output returned empty constraints for schema: {schema} "
                        f"with {attribute_count} attributes. Falling back to raw output parsing."
                    )
                    raise LLMValidationError(
                        "Empty constraints returned from structured output",
                        provider="openai",
                        model="gpt-4o-mini",
                        request_id=None,
                    )
                else:
                    # No attributes, empty result is expected
                    logger.debug(
                        f"Structured output returned empty constraints for schema: {schema} "
                        "(no attributes provided)"
                    )
                    return result

        except (LLMValidationError, LLMError) as e:
            logger.debug(
                f"Structured output failed for schema: {schema}, error: {e}. "
                "Attempting fallback to raw output parsing."
            )

            # Fallback: Use raw output and parse manually
            try:
                # Enhanced prompt for raw output
                fallback_system = (
                    self.SYSTEM_PROMPT
                    + "\n\nCRITICAL: You MUST return valid JSON in this exact format:\n"
                    + '{"constraints": {"attribute_name": "constraint_description", ...}}\n'
                    + "Do not include any markdown formatting, explanations, or additional text. "
                    + "Return ONLY the JSON object."
                )

                raw_response = await ask(
                    prompt=prompt,
                    system=fallback_system,
                    temperature=0.3,
                )

                # Parse JSON from response
                parsed = self._parse_json_from_text(raw_response)
                if parsed and "constraints" in parsed:
                    constraints = parsed["constraints"]
                    if constraints:
                        result = ResponsePropertyConstraintsOutput(
                            constraints=constraints
                        )
                        logger.info(
                            f"Fallback parsing successful: schema={schema}, "
                            f"constraints_count={len(result.constraints)}"
                        )
                        return result
                    else:
                        logger.warning(
                            f"Fallback parsing returned empty constraints for schema: {schema}"
                        )
                        # Return empty result but log warning
                        return ResponsePropertyConstraintsOutput(constraints={})
                else:
                    raise LLMError(
                        f"Failed to parse constraints from raw output. "
                        f"Response preview: {raw_response[:200]}",
                        provider="openai",
                        model="gpt-4o-mini",
                    )

            except Exception as fallback_error:
                logger.error(
                    f"Both structured output and fallback parsing failed for schema: {schema}. "
                    f"Structured error: {e}, Fallback error: {fallback_error}"
                )
                raise LLMError(
                    f"Failed to extract constraints: {fallback_error}",
                    provider="openai",
                    model="gpt-4o-mini",
                ) from fallback_error

    async def extract_response_property_constraints(
        self, schema: str, attributes: str
    ) -> ResponsePropertyConstraintsOutput:
        """Extract constraints from response schema attributes.

        Analyzes schema attributes and extracts constraints, rules, and
        limitations that can be programmatically validated.

        Uses structured output as primary method with automatic fallback
        to raw output parsing if structured output fails or returns empty results.

        Args:
            schema: Schema name to analyze
            attributes: Formatted attribute descriptions (one per line with "- " prefix)

        Returns:
            ResponsePropertyConstraintsOutput containing extracted constraints mapping
            attribute names to constraint descriptions

        Raises:
            LLMError: If LLM call fails after retries and fallback
        """
        prompt = self.USER_PROMPT.format(schema=schema, attributes=attributes)
        attribute_count = attributes.count("- ")
        logger.debug(
            f"ResponsePropertyConstraintMiner prompt: schema={schema}, "
            f"prompt_length={len(prompt)}, attributes_count={attribute_count}"
        )

        try:
            result = await self._extract_with_fallback(prompt, schema, attributes)

            # Final validation and logging
            if not result.constraints:
                if attribute_count > 0:
                    logger.warning(
                        f"No constraints extracted for schema: {schema} "
                        f"despite {attribute_count} attributes provided. "
                        "This may indicate the attributes have no verifiable constraints."
                    )
                else:
                    logger.debug(
                        f"No constraints extracted for schema: {schema} "
                        "(no attributes provided)"
                    )

            logger.debug(
                f"ResponsePropertyConstraintMiner result: schema={schema}, "
                f"constraints_count={len(result.constraints)}"
            )
            return result

        except LLMError as e:
            logger.error(
                f"Failed to extract response property constraints: schema={schema}, "
                f"error={str(e)}, error_type={type(e).__name__}"
            )
            raise


async def main():
    extractor = ResponsePropertyConstraintMiner()
    result = await extractor.extract_response_property_constraints(
        schema="User",
        attributes="- name: a string attribute...\n- age: an integer attribute, between 18 and 100",
    )
    logger.info(f"ResponsePropertyConstraintMiner result: {result.constraints}")


if __name__ == "__main__":
    asyncio.run(main())

__all__ = ["ResponsePropertyConstraintMiner"]
