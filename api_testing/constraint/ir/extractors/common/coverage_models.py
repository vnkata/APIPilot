"""
Common models for coverage checking.

Defines Pydantic models for LLM-driven coverage check responses.
"""

from pydantic import BaseModel, Field


class CoverageCheckResult(BaseModel):
    """Result from LLM coverage check.

    Determines if existing constraints sufficiently cover all requirements
    from the specification description.

    Attributes:
        is_sufficient: Whether existing constraints are sufficient
        missing_constraints: Descriptions of missing constraints (natural language)
        reasoning: Explanation of the coverage decision

    Example:
        >>> result = CoverageCheckResult(
        ...     is_sufficient=False,
        ...     missing_constraints=["Must be a valid email format"],
        ...     reasoning="Email format validation is mentioned but not covered"
        ... )
    """

    is_sufficient: bool = Field(
        ..., description="True if existing constraints are sufficient"
    )
    missing_constraints: list[str] = Field(
        default_factory=list,
        description="Natural language descriptions of missing constraints",
    )
    reasoning: str = Field(
        ..., description="Explanation of coverage decision and what is/isn't covered"
    )


__all__ = ["CoverageCheckResult"]
