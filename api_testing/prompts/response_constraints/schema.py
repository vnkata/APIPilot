"""
Pydantic models for response constraint extraction.

These models define the structure of constraints extracted from
response schema attributes.
"""

from typing import Dict
from pydantic import BaseModel, Field, field_validator


class ResponsePropertyConstraintsOutput(BaseModel):
    """Output model for response property constraints extraction.

    Contains a mapping of response property names to constraint descriptions of a schema.

    Attributes:
        constraints: Dictionary mapping response property names to constraint descriptions.
            Keys are attribute names, values are constraint descriptions.
    """

    constraints: Dict[str, str] = Field(
        description=(
            "Map of response property names to constraint descriptions. "
            "Each key is an attribute name, each value is a concise constraint description "
            "that can be used for automated validation (e.g., 'Integer between 1 and 32', "
            "'ISO date format (YYYY-MM-DD)', 'Must be 1 or 0'). "
            "Only include attributes that have verifiable constraints."
        ),
        default_factory=dict,
        examples=[
            {
                "id": "Integer between 1 and 32",
                "date": "ISO date format (YYYY-MM-DD)",
                "federal": "Must be 1 or 0",
            }
        ],
    )

    @field_validator("constraints")
    @classmethod
    def validate_constraints_not_empty_when_expected(
        cls, v: Dict[str, str]
    ) -> Dict[str, str]:
        """Validate that constraints dict is properly structured.

        Note: We don't enforce non-empty here because empty constraints
        might be valid if no constraints can be identified. The extraction
        logic handles empty constraint validation.
        """
        # Ensure all values are non-empty strings
        return {k: v for k, v in v.items() if v and isinstance(v, str)}
