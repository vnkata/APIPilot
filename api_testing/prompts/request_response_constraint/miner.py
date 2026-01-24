"""
Request-Response constraints extraction prompt class.

Extracts constraints between request parameters and response properties using validation-based approach:
1. LLM validates which request-response pairs have constraints (bool)
2. Generate constraint descriptions for validated pairs
"""

import asyncio
from typing import Dict
from common.llm import ask
from common.llm.exceptions import LLMError
from common.llm.extractors import StructuredOutputExtractor
from common.logger import get_logger, LogLevel
from api_testing.prompts.request_response_constraint.schema import (
    RequestResponseConstraintOutput,
    RequestResponseConstraintValidation,
)
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("request_response_constraints", level=LogLevel.DEBUG)

# System prompt for validation
REQUEST_RESPONSE_VALIDATION_SYSTEM_PROMPT = """You are an expert at analyzing API operations and identifying constraint relationships between request parameters and response properties.

**CRITICAL: What TO Mark as Having Constraints**

Only mark True for request-response pairs that have a **verifiable, programmatic relationship**:

1. **Filtering Constraints**:
   - Request parameter filters response data (e.g., `filter[status]=active` → only active items in response)
   - Query parameter affects which response properties are returned

2. **Sorting/Ordering Constraints**:
   - Request parameter controls response order (e.g., `sort=name` → response sorted by name field)
   
3. **Pagination Constraints**:
   - Request parameter limits response size (e.g., `limit=10` → max 10 items in response)
   - Offset/page parameter affects which subset is returned

4. **Projection/Field Selection**:
   - Request parameter controls which fields appear in response (e.g., `fields=id,name` → only those fields)

5. **Transformation Constraints**:
   - Request parameter transforms response data format (e.g., `format=summary` → condensed response)

6. **Validation Constraints**:
   - Request parameter value must match or relate to response property value
   - ID in request must equal ID in response

**What NOT to Mark**:
- Generic relationships without specific constraint logic
- Unrelated request-response pairs
- Implicit relationships without verification rules

**Output Format:**
Return ONLY valid JSON without markdown formatting:

{
  "constraints": {
    "request_param_name": {
      "response_property_path": true/false
    }
  }
}

**Important:**
- Return True ONLY if there's a clear, testable constraint relationship
- Return False for unrelated or unclear relationships
- Use lowercase `true` and `false` (JSON boolean format)
"""

REQUEST_RESPONSE_VALIDATION_USER_PROMPT = """Analyze the following API operation and determine which request parameters have constraint relationships with response properties.

Operation: {operation_name}
Method: {method}
Path: {path}

Request Parameters:
{request_params}

Response Properties:
{response_properties}

For each request parameter, evaluate if it has a constraint relationship with any response property. Return a nested JSON object mapping request parameters to response properties with boolean indicators.
"""


class RequestResponseConstraintMiner:
    """Extracts constraints between request parameters and response properties.

    Approach:
    1. LLM validates which request-response pairs have constraints → Dict[str, Dict[str, bool]]
    2. Generate descriptions for validated pairs using templates or LLM
    3. Return nested structure mapping request params to response properties

    Example:
        >>> miner = RequestResponseConstraintMiner()
        >>> result = await miner.extract_constraints(
        ...     operation_name="listHolidays",
        ...     method="GET",
        ...     path="/holidays",
        ...     request_params="- filter[status]: string, filters by status\\n- limit: integer, limits results",
        ...     response_properties="- items[].status: string\\n- items[].name: string"
        ... )
        >>> print(result.constraints)
        # {"filter[status]": {"items[].status": "Request filters response by matching status values"}}
    """

    SYSTEM_PROMPT: str = REQUEST_RESPONSE_VALIDATION_SYSTEM_PROMPT
    USER_PROMPT: str = REQUEST_RESPONSE_VALIDATION_USER_PROMPT

    def __init__(self) -> None:
        """Initialize RequestResponseConstraintMiner."""
        pass

    def _generate_constraint_description(
        self,
        request_param: str,
        response_property: str,
        request_param_desc: str,
        response_property_desc: str,
    ) -> str:
        """Generate human-readable constraint description.

        Args:
            request_param: Name of request parameter
            response_property: Path to response property
            request_param_desc: Description of request parameter
            response_property_desc: Description of response property

        Returns:
            Human-readable constraint description
        """
        # Template-based generation for common patterns
        param_lower = request_param.lower()

        if "filter" in param_lower or "status" in param_lower:
            return f"Request parameter '{request_param}' filters response property '{response_property}' by matching values"

        if "sort" in param_lower or "order" in param_lower:
            return f"Request parameter '{request_param}' controls sorting order of '{response_property}' in response"

        if "limit" in param_lower or "page" in param_lower or "offset" in param_lower:
            return f"Request parameter '{request_param}' controls pagination affecting '{response_property}' count/subset"

        if "field" in param_lower or "select" in param_lower:
            return f"Request parameter '{request_param}' controls whether '{response_property}' appears in response"

        # Generic fallback
        return f"Request parameter '{request_param}' has constraint relationship with response property '{response_property}'"

    def _parse_params_string(self, params: str) -> Dict[str, str]:
        """Parse parameter string to extract names and descriptions.

        Args:
            params: Formatted parameter descriptions (one per line with "- " prefix)

        Returns:
            Dictionary mapping parameter names to descriptions
        """
        param_dict: Dict[str, str] = {}

        lines = params.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or not line.startswith("- "):
                continue

            content = line[2:].strip()
            if ":" in content:
                name, description = content.split(":", 1)
                param_dict[name.strip()] = description.strip()

        return param_dict

    async def extract_constraints(
        self,
        operation_name: str,
        method: str,
        path: str,
        request_params: str,
        response_properties: str,
    ) -> RequestResponseConstraintOutput:
        """Extract request-response constraints using validation-based approach.

        Steps:
        1. Call LLM to validate which request-response pairs have constraints
        2. Extract validation result using StructuredOutputExtractor
        3. For validated pairs, generate constraint descriptions
        4. Return nested Dict[str, Dict[str, str]]

        Args:
            operation_name: Name/ID of the API operation
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            request_params: Formatted request parameter descriptions
            response_properties: Formatted response property descriptions

        Returns:
            RequestResponseConstraintOutput with nested constraint mappings

        Raises:
            LLMError: If LLM call or extraction fails
        """
        request_count = request_params.count("- ")
        response_count = response_properties.count("- ")

        logger.debug(
            f"Validating request-response constraints: operation={operation_name}, "
            f"request_params={request_count}, response_properties={response_count}"
        )

        # Step 1: Call LLM for validation
        prompt = self.USER_PROMPT.format(
            operation_name=operation_name,
            method=method,
            path=path,
            request_params=request_params,
            response_properties=response_properties,
        )

        try:
            raw_response = await ask(
                prompt=prompt,
                system=self.SYSTEM_PROMPT,
                temperature=0.1,
            )
            logger.debug(
                f"LLM validation response received: operation={operation_name}, "
                f"response_length={len(raw_response)}"
            )
        except LLMError as e:
            logger.error(
                f"LLM call failed for operation: {operation_name}, error={str(e)}"
            )
            raise

        # Step 2: Extract validation result
        try:
            validation_result: RequestResponseConstraintValidation = (
                StructuredOutputExtractor.extract(
                    raw_text=raw_response,
                    model_class=RequestResponseConstraintValidation,
                    strict=True,
                )
            )
            logger.debug(
                f"Validation extraction successful: operation={operation_name}, "
                f"validated_params={len(validation_result.constraints)}"
            )
        except Exception as e:
            logger.error(
                f"Failed to extract validation result for operation: {operation_name}, "
                f"error={str(e)}, raw_response_preview={raw_response[:200]}"
            )
            raise LLMError(
                f"Failed to extract validation result: {str(e)}",
                provider="extractor",
                model="validation",
            ) from e

        # Step 3: Parse parameter strings for descriptions
        request_param_descs = self._parse_params_string(request_params)
        response_property_descs = self._parse_params_string(response_properties)

        # Step 4: Build final output with descriptions
        final_constraints: Dict[str, Dict[str, str]] = {}

        for request_param, response_map in validation_result.constraints.items():
            if not response_map:
                continue

            final_constraints[request_param] = {}

            for response_property, has_constraint in response_map.items():
                if has_constraint:
                    # Generate description
                    description = self._generate_constraint_description(
                        request_param=request_param,
                        response_property=response_property,
                        request_param_desc=request_param_descs.get(request_param, ""),
                        response_property_desc=response_property_descs.get(
                            response_property, ""
                        ),
                    )

                    final_constraints[request_param][response_property] = description
                    logger.debug(
                        f"Added constraint: {request_param} -> {response_property}: {description}"
                    )

        logger.info(
            f"Request-response constraint extraction complete: operation={operation_name}, "
            f"validated_pairs={sum(len(v) for v in final_constraints.values())}"
        )

        return RequestResponseConstraintOutput(constraints=final_constraints)


async def main():
    """Test the request-response constraint extraction."""
    miner = RequestResponseConstraintMiner()

    result = await miner.extract_constraints(
        operation_name="listHolidays",
        method="GET",
        path="/api/holidays",
        request_params="""- filter[status]: string, filters holidays by status
- limit: integer, maximum number of results to return
- sort: string, field to sort results by""",
        response_properties="""- data[].id: integer, unique holiday identifier
- data[].status: string, current status of the holiday
- data[].name: string, name of the holiday
- meta.total: integer, total count of matching holidays""",
    )

    logger.info(f"Test result: {result.constraints}")


if __name__ == "__main__":
    asyncio.run(main())


__all__ = ["RequestResponseConstraintMiner"]
