"""
Pydantic models for response constraint extraction.

These models define the structure of constraints extracted from
response schema attributes.
"""

from pydantic import BaseModel, Field, field_validator


class ResponsePropertyConstraintsValidation(BaseModel):
    """LLM output: validation of which attributes have constraints.

    Contains boolean flags indicating whether each attribute has
    non-trivial constraints beyond basic type validation.

    This model is used for the validation-based approach where LLM
    only determines yes/no if an attribute has constraints, rather
    than generating constraint descriptions.

    Attributes:
        constraints: Dictionary mapping attribute names to boolean flags.
            True = attribute has non-trivial constraints
            False = only basic type validation
    """

    constraints: dict[str, bool] = Field(
        description=(
            "Map of attribute names to boolean flags. "
            "True = attribute has non-trivial constraints (enum, format, range, pattern, etc.), "
            "False = only basic type validation (String, Integer, Boolean, Array). "
            "Only include attributes you analyzed. "
            "Do NOT include attributes with only trivial type information."
        ),
        default_factory=dict,
        examples=[
            {"id": True, "date": True, "name": False},
            {"federal": True, "observedDate": True, "nameEn": False},
        ],
    )

    @field_validator("constraints")
    @classmethod
    def validate_constraints_structure(cls, v: dict[str, bool]) -> dict[str, bool]:
        """Validate that constraints dict contains only boolean values."""
        for key, value in v.items():
            if not isinstance(value, bool):
                raise ValueError(
                    f"Constraint value for '{key}' must be bool, got {type(value).__name__}"
                )
        return v


class ResponsePropertyConstraintsValidationV2(BaseModel):
    """Validation result from LLM indicating which properties have constraints.

    Optimized format: only list properties WITH constraints (no false values).
    """

    constrained_properties: list[str] = Field(
        default_factory=list,
        description="List of property paths that have validation constraints",
    )


class ResponsePropertyConstraintsOutput(BaseModel):
    """Output model for response property constraints extraction.

    Contains a mapping of response property names to constraint descriptions of a schema.
    Only includes non-trivial constraints that go beyond basic type validation.

    Attributes:
        constraints: Dictionary mapping response property names to constraint descriptions.
            Keys are attribute names, values are constraint descriptions.
            Only includes non-trivial constraints (e.g., ranges, formats, enums, patterns).
            Does NOT include basic type information (String, Integer, Boolean, Array).
    """

    constraints: dict[str, str] = Field(
        description=(
            "Map of response property names to non-trivial constraint descriptions. "
            "Each key is an attribute name, each value is a concise constraint description "
            "that can be used for automated validation. "
            "ONLY include constraints that go beyond basic type validation: "
            "- Range constraints (e.g., 'Integer between 1 and 32') "
            "- Format constraints (e.g., 'ISO date format (YYYY-MM-DD)') "
            "- Enum constraints (e.g., 'Must be 1 or 0', 'Must be one of [\"public\", \"private\"]') "
            "- Pattern constraints (e.g., 'Must match pattern: ^[A-Z]+$') "
            "DO NOT include basic type information like 'String', 'Integer', 'Boolean', or 'Array'. "
            "Only include attributes that have verifiable non-trivial constraints."
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
        cls, v: dict[str, str]
    ) -> dict[str, str]:
        """Validate that constraints dict is properly structured.

        Note: We don't enforce non-empty here because empty constraints
        might be valid if no constraints can be identified. The extraction
        logic handles empty constraint validation.
        """
        # Ensure all values are non-empty strings
        return {k: v for k, v in v.items() if v and isinstance(v, str)}
