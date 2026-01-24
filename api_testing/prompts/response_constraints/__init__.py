"""
Response constraints extraction prompt class.

Extracts constraints from response schema attributes using validation-based approach:
1. LLM validates which attributes have non-trivial constraints (bool)
2. Use schema's to_human_readable() for constraint descriptions
"""

import asyncio
import re
from typing import Dict, Optional
from common.llm import ask
from common.llm.exceptions import LLMError
from common.llm.extractors import StructuredOutputExtractor
from common.logger import get_logger, LogLevel
from api_testing.prompts.response_constraints.schema import (
    ResponsePropertyConstraintsOutput,
    ResponsePropertyConstraintsValidation,
)
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("response_constraints", level=LogLevel.DEBUG)

# Validation-based prompt: LLM returns Dict[str, bool] indicating which attributes have constraints
RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_SYSTEM_PROMPT = """You are an expert at analyzing API schema attributes and identifying which attributes have non-trivial, programmatically verifiable constraints.

**CRITICAL: What NOT to Mark as Having Constraints**
DO NOT mark attributes that only have basic type information:
- Attributes with only basic type (String, Integer, Boolean, Array)
- Attributes without explicit constraints beyond their type

**What TO Mark as Having Constraints**
Only mark True for attributes with constraints BEYOND basic schema validation:

1. **Explicit Schema Constraints**:
   - format is specified (e.g., date-time, uri, email)
   - enum is specified (allowed value list)
   - minimum, maximum, minLength, maxLength are specified
   - pattern is specified (regex)
   - minItems, maxItems, uniqueItems for arrays

2. **Explicit Description-Based Constraints**:
   - Description mentions specific format requirements
   - Description lists allowed values
   - Description states numeric or length limits
   - Description describes pattern requirements

3. **Semantic Constraints** (ONLY if explicitly stated):
   - Extract ONLY if description explicitly states a constraint rule
   - Example: "must be a positive integer" means mark True
   - Example: "must be 1 or 0" means mark True
   - DO NOT infer constraints from names alone

**Decision Rules:**
- If attribute has enum, format, minimum, maximum, minLength, maxLength, pattern: Mark True
- If description explicitly states a constraint rule: Mark True
- If attribute only has basic type info: Mark False
- If uncertain: Mark False

**Output Format:**
Return ONLY valid JSON without markdown formatting:

{
  "constraints": {
    "attribute_name": true/false
  }
}

**Important:**
- Return True ONLY if you are confident the attribute has non-trivial constraints
- Return False for attributes with only basic type information
- Include ALL attributes you analyzed in the output
- Use lowercase `true` and `false` (JSON boolean format)
- Do not add comments (//) in the actual JSON output
"""

RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_USER_PROMPT = """Please analyze the following schema and its attributes. For each attribute, determine if it has non-trivial constraints beyond basic type validation.

Schema: {schema}
Attributes:
{attributes}

Return a JSON object with "constraints" field mapping each attribute name to true (has non-trivial constraints) or false (only basic type).
"""


class ResponsePropertyConstraintMiner:
    """Extracts constraints from response schema attributes using validation-based LLM approach.

    New approach (validation-based):
    1. LLM validates which attributes have non-trivial constraints → Dict[str, bool]
    2. For validated attributes (True), use schema's to_human_readable() for description
    3. Return only attributes with constraints → Dict[str, str]

    Benefits:
    - Reduced hallucination (yes/no vs text generation)
    - Consistent descriptions from schema
    - Cleaner separation of concerns

    Example:
        >>> from api_testing.prompts.response_constraints import ResponsePropertyConstraintMiner
        >>> extractor = ResponsePropertyConstraintMiner()
        >>> result = await extractor.extract_response_property_constraints(
        ...     schema="Holiday",
        ...     attributes="- id: an integer, minimum: 1, maximum: 32\\n- name: a string",
        ...     flattened_schema={"id": ItemProperties(...), "name": ItemProperties(...)}
        ... )
        >>> print(result.constraints)  # {"id": "an integer, minimum: 1, maximum: 32"}
    """

    SYSTEM_PROMPT: str = RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_SYSTEM_PROMPT
    USER_PROMPT: str = RESPONSE_PROPERTY_CONSTRAINTS_VALIDATION_USER_PROMPT

    def __init__(self, llm: Optional[object] = None) -> None:
        """Initialize ResponseConstraints extractor.

        Args:
            llm: Deprecated parameter (kept for backward compatibility).
                The class now uses common.llm directly.
        """
        pass

    def _parse_attributes_string(self, attributes: str) -> Dict[str, str]:
        """Parse attributes string to extract attribute names and their descriptions.

        Args:
            attributes: Formatted attribute descriptions (one per line with "- " prefix)
                Example: "- id: an integer, minimum: 1\\n- name: a string"

        Returns:
            Dictionary mapping attribute names to their full descriptions
            Example: {"id": "an integer, minimum: 1", "name": "a string"}
        """
        attr_dict: Dict[str, str] = {}

        # Split by lines and process each attribute
        lines = attributes.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or not line.startswith("- "):
                continue

            # Remove "- " prefix
            content = line[2:].strip()

            # Split on first colon to get name and description
            if ":" in content:
                name, description = content.split(":", 1)
                attr_dict[name.strip()] = description.strip()

        logger.debug(f"Parsed {len(attr_dict)} attributes from string")
        return attr_dict

    async def extract_response_property_constraints(
        self, schema: str, attributes: str, flattened_schema: Optional[Dict] = None
    ) -> ResponsePropertyConstraintsOutput:
        """Extract constraints using validation-based approach.

        Steps:
        1. Call LLM to validate which attributes have non-trivial constraints
        2. Extract validation result using StructuredOutputExtractor
        3. For attributes with constraints=True, use their description from attributes string
        4. Return Dict[str, str] with only validated attributes

        Args:
            schema: Schema name to analyze
            attributes: Formatted attribute descriptions (one per line with "- " prefix)
            flattened_schema: Optional dict mapping attribute names to ItemProperties
                (for future enhancement if we want to use ItemProperties.to_human_readable())

        Returns:
            ResponsePropertyConstraintsOutput containing only attributes with non-trivial constraints

        Raises:
            LLMError: If LLM call or extraction fails
        """
        attribute_count = attributes.count("- ")
        logger.debug(
            f"Validating constraints for schema: {schema}, attributes_count={attribute_count}"
        )

        # Step 1: Call LLM for validation (NO response_model - raw text output)
        prompt = self.USER_PROMPT.format(schema=schema, attributes=attributes)
        try:
            raw_response = await ask(
                prompt=prompt,
                system=self.SYSTEM_PROMPT,
                temperature=0.1,  # Lower temperature for yes/no decisions
            )
            logger.debug(
                f"LLM validation response received: schema={schema}, "
                f"response_length={len(raw_response)}"
            )
        except LLMError as e:
            logger.error(f"LLM call failed for schema: {schema}, error={str(e)}")
            raise

        # Step 2: Extract validation result using StructuredOutputExtractor
        try:
            validation_result: ResponsePropertyConstraintsValidation = (
                StructuredOutputExtractor.extract(
                    raw_text=raw_response,
                    model_class=ResponsePropertyConstraintsValidation,
                    strict=True,
                )
            )
            logger.debug(
                f"Validation extraction successful: schema={schema}, "
                f"validated_count={len(validation_result.constraints)}"
            )
        except Exception as e:
            logger.error(
                f"Failed to extract validation result for schema: {schema}, "
                f"error={str(e)}, raw_response_preview={raw_response[:200]}"
            )
            raise LLMError(
                f"Failed to extract validation result: {str(e)}",
                provider="extractor",
                model="validation",
            ) from e

        # Step 3: Parse attributes string to get descriptions
        attr_descriptions = self._parse_attributes_string(attributes)

        # Step 4: Build final output - only attributes with constraints=True
        final_constraints: Dict[str, str] = {}
        for attr_name, has_constraint in validation_result.constraints.items():
            if has_constraint:
                # Get description from attributes string
                description = attr_descriptions.get(attr_name, "")
                if description:
                    final_constraints[attr_name] = description
                    logger.debug(f"Added constraint for {attr_name}: {description}")
                else:
                    logger.warning(
                        f"Attribute {attr_name} validated as having constraint "
                        f"but description not found in attributes string"
                    )

        logger.info(
            f"Constraint validation complete: schema={schema}, "
            f"total_attributes={attribute_count}, "
            f"validated_with_constraints={len(final_constraints)}"
        )

        return ResponsePropertyConstraintsOutput(constraints=final_constraints)


async def main():
    """Test the constraint validation approach."""
    extractor = ResponsePropertyConstraintMiner()

    # Test with sample attributes
    test_attributes = """- id: an integer, minimum: 1, maximum: 32
- name: a string
- date: a string, format date
- federal: an integer, values in of [1, 0]
- description: a string"""

    result = await extractor.extract_response_property_constraints(
        schema="Holiday", attributes=test_attributes
    )
    logger.info(f"Test result: {result.constraints}")


if __name__ == "__main__":
    asyncio.run(main())

__all__ = ["ResponsePropertyConstraintMiner"]
