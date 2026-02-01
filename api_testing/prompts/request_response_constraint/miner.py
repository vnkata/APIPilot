"""
Request-Response constraints extraction prompt class.

Extracts constraints between request parameters and response properties using validation-based approach:
1. LLM validates which request-response pairs have constraints (bool)
2. Generate constraint descriptions for validated pairs
"""

import asyncio
from typing import Dict, Optional

from common.llm.exceptions import LLMError
from common.logger import get_logger, LogLevel
from api_testing.prompts.request_response_constraint.schema import (
    RequestResponseConstraintOutput,
    RequestResponseConstraintValidationV2,
)
from api_testing.prompts.request_response_constraint.prompts import (
    REQUEST_RESPONSE_VALIDATION_SYSTEM_PROMPT_V2,
    REQUEST_RESPONSE_VALIDATION_USER_PROMPT_V2,
)
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("request_response_constraints", level=LogLevel.DEBUG)


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

    SYSTEM_PROMPT: str = REQUEST_RESPONSE_VALIDATION_SYSTEM_PROMPT_V2
    USER_PROMPT: str = REQUEST_RESPONSE_VALIDATION_USER_PROMPT_V2

    def __init__(
        self,
        model: Optional["APITestingBaseLLMModel"] = None,
        temperature: float = 0.1,
        **llm_kwargs,
    ) -> None:
        """Initialize RequestResponseConstraintMiner.

        Args:
            model: LLM model instance. If None, uses factory default from env vars.
            temperature: Sampling temperature for LLM calls (default: 0.1 for deterministic validation)
            **llm_kwargs: Additional LLM parameters (max_tokens, etc.)
        """
        if model is None:
            # Import here to avoid circular dependency
            from api_testing.models.llms.factory import ModelFactory

            self.model = ModelFactory.get_default()
            logger.debug(
                "Using factory default model for RequestResponseConstraintMiner"
            )
        else:
            self.model = model
            logger.debug(f"Using injected model: {self.model.get_model_name()}")

        self.temperature = temperature
        self.llm_kwargs = llm_kwargs

    def _generate_constraint_description(
        self,
        request_param: str,
        response_property: str,
    ) -> str:
        """Generate human-readable constraint description.

        Args:
            request_param: Name of request parameter
            response_property: Path to response property

        Returns:
            Human-readable constraint description
        """
        # Template-based generation for common patterns
        param_lower = request_param.lower()

        # Echo/ID matching pattern
        if "id" in param_lower and "id" in response_property.lower():
            return f"Request parameter '{request_param}' must match response property '{response_property}'"

        # Filtering pattern
        if "filter" in param_lower or param_lower in response_property.lower():
            return f"Request parameter '{request_param}' filters response property '{response_property}' by matching values"

        # Sorting pattern
        if "sort" in param_lower or "order" in param_lower:
            return f"Request parameter '{request_param}' controls sorting order of '{response_property}' in response"

        # Pagination pattern
        if "limit" in param_lower or "page" in param_lower or "offset" in param_lower:
            return f"Request parameter '{request_param}' controls pagination affecting '{response_property}' count/subset"

        # Field selection pattern
        if "field" in param_lower or "select" in param_lower:
            return f"Request parameter '{request_param}' controls whether '{response_property}' appears in response"

        # Generic fallback
        return f"Request parameter '{request_param}' has constraint relationship with response property '{response_property}'"

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
        2. Extract validation result using model's structured output capability
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

        # Step 1: Call LLM for validation using injected model
        prompt = self.USER_PROMPT.format(
            operation_name=operation_name,
            method=method,
            path=path,
            request_params=request_params,
            response_properties=response_properties,
        )

        try:
            validation_result: RequestResponseConstraintValidationV2 = (
                await self.model.a_generate(
                    prompt=prompt,
                    system_prompt=self.SYSTEM_PROMPT,
                    schema=RequestResponseConstraintValidationV2,
                    temperature=self.temperature,
                    **self.llm_kwargs,
                )
            )

            logger.debug(
                f"Validation successful: operation={operation_name}, "
                f"validated_params={len(validation_result.request_response_pairs)}"
            )

        except LLMError as e:
            logger.error(
                f"LLM call failed for operation: {operation_name}, error={str(e)}"
            )
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error during validation for operation: {operation_name}, "
                f"error={str(e)}"
            )
            raise LLMError(
                f"Failed to validate request-response constraints: {str(e)}",
                provider="validation",
                model=self.model.get_model_name(),
            ) from e

        # Step 2: Build final output with descriptions
        final_constraints: Dict[str, Dict[str, str]] = {}

        for pair in validation_result.request_response_pairs:
            request_param = pair.request_param

            if not pair.response_properties:
                continue

            if request_param not in final_constraints:
                final_constraints[request_param] = {}

            for response_property in pair.response_properties:
                # Generate description
                description = self._generate_constraint_description(
                    request_param=request_param,
                    response_property=response_property,
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
