"""
Pydantic models for request-response constraint extraction.

These models define the structure of constraints extracted between
API request parameters and response properties.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RequestResponseConstraintItem(BaseModel):
    """Single request-response constraint mapping.

    Represents how a request parameter affects or corresponds to
    a response property.

    Attributes:
        parameter: Parameter name(s), comma-separated if multiple
        description: Constraint description in natural language
        property: Response property name that corresponds to this parameter
    """

    parameter: str = Field(description="Parameter name(s), comma-separated if multiple")
    description: str = Field(description="Constraint description in natural language")
    property: Optional[str] = Field(
        default=None,
        description="Response property name that corresponds to this parameter",
    )


class RequestResponseConstraintVerdict(BaseModel):
    """Container for request-response constraint mappings.

    Contains a list of constraints that map request parameters
    to response properties.

    Attributes:
        constraint: List of constraint mappings
    """

    constraint: List[RequestResponseConstraintItem] = Field(
        description="List of parameter-to-response-property constraint mappings"
    )


# Backward compatibility aliases
ReqResConstraintVerdict = RequestResponseConstraintItem
Verdict = RequestResponseConstraintVerdict
