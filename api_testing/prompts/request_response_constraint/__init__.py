"""
Request-response constraint extraction prompt class.

Maps request parameters to response properties and extracts constraints
that define how parameters influence response schemas.
"""

from typing import Optional
from common.llm import ask
from common.llm.exceptions import LLMError
from common.logger.utils.helpers import get_logger
from api_testing.prompts.request_response_constraint.schema import (
    RequestResponseConstraintVerdict,
)


class RequestResponseConstraint:
    """Extracts constraints between request parameters and response properties.

    This class uses structured LLM outputs to identify how request parameters
    affect or correspond to response schema properties.

    Example:
        >>> from api_testing.prompts.request_response_constraint import RequestResponseConstraint
        >>> extractor = RequestResponseConstraint(
        ...     endpoint="GET /api/users",
        ...     parameters="limit: integer parameter...",
        ...     response="User schema...",
        ...     extras="Additional context..."
        ... )
        >>> result = await extractor.validate()
        >>> print(result.constraint)
    """

    SYSTEM_PROMPT = """Given a list of parameters and an API response schema, It is your responsibility to verify how each input parameter influences the API response schema.
Determines how a property is affected by a query parameter or how a query parameter affects a response schema.
Some cases can help determine a corresponding attribute:
- If the input parameter is null or omitted, the default value defined for the query parameter will be used (if a default is specified).
- The input parameter is used for filtering, and its corresponding attribute—representing the actual value after filtering—must exist within the same object as the input parameter.
- Constraints on input parameters—such as min, max, format, or allowed values (e.g., enum) - should align with the constraints of the corresponding response properties. For example, if input.limit ∈ (1, 2, 3) and input.limit = response.limit, then response.limit must also satisfy response.limit ∈ (1, 2, 3).
- The input parameter and the corresponding response attribute should represent the same concept and interpret their values consistently.
Eg:
    - ((input.limit or 20) >= sizeOf(return)) and sizeOf(return) >= 0 and sizeOf(return) <= 100 # 20 is default value of input.limit
    - ((input.month or 1) = monthOfDay(return.date)) and (input.month >= 1 and input.month <=12)
    ....
Return a JSON object with a "constraint" field containing a list of objects. Each object has "parameter", "description", and "property" fields."""

    PROMPT = """Endpoint: {endpoint}
Here is list parameters and response schema
*Parameters:*
{parameters}
*Response schema:*
{response}
*Additional Information*: 
{additional_information}"""

    def __init__(
        self,
        llm: Optional[object] = None,
        endpoint: str = "",
        parameters: str = "",
        response: str = "",
        extras: str = "",
    ) -> None:
        """Initialize RequestResponseConstraint extractor.

        Args:
            llm: Deprecated parameter (kept for backward compatibility).
                The class now uses src/common/llm directly.
            endpoint: API endpoint path and method (e.g., "GET /api/users")
            parameters: Formatted parameter descriptions
            response: Response schema description
            extras: Additional context or information
        """
        self.endpoint = endpoint
        self.parameters = parameters
        self.response = response
        self.extras = extras
        self.logger = get_logger(__name__)

    async def validate(self) -> RequestResponseConstraintVerdict:
        """Extract constraints between request parameters and response properties.

        Analyzes the relationship between request parameters and response schema
        to identify constraint mappings and validation rules.

        Returns:
            RequestResponseConstraintVerdict containing list of constraint mappings

        Raises:
            LLMError: If LLM call fails after retries
        """
        prompt = self.PROMPT.format(
            endpoint=self.endpoint,
            parameters=self.parameters,
            response=self.response,
            additional_information=self.extras,
        )
        self.logger.debug(
            f"RequestResponseConstraint prompt: endpoint={self.endpoint}, prompt_length={len(prompt)}"
        )

        try:
            result = await ask(
                prompt=prompt,
                system=self.SYSTEM_PROMPT,
                response_model=RequestResponseConstraintVerdict,
                temperature=0.3,  # Lower temperature for more deterministic constraint extraction
            )
            self.logger.debug(
                f"RequestResponseConstraint result: endpoint={self.endpoint}, constraints_count={len(result.constraint)}"
            )
            return result
        except LLMError as e:
            self.logger.error(
                f"Failed to extract request-response constraints: endpoint={self.endpoint}, error={str(e)}, error_type={type(e).__name__}"
            )
            raise

    def __str__(self) -> str:
        """String representation of the constraint extractor."""
        return f"RequestResponseConstraint(endpoint={self.endpoint}, parameters={len(self.parameters)} chars, response={len(self.response)} chars)"


__all__ = ["RequestResponseConstraint"]
