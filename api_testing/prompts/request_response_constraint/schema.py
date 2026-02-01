"""Pydantic models for request-response constraint extraction."""

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class ReqResConstraintVerdict(BaseModel):
    parameter: str
    description: str
    property: str

    def to_dict(self):
        return {
            "parameter": self.parameter,
            "description": self.description,
            "property": self.property,
        }


@dataclass
class Verdict(BaseModel):
    constraint: list[ReqResConstraintVerdict]

    def to_dict(self):
        return {"constraint": [item.to_dict() for item in self.constraint]}


class RequestResponsePair(BaseModel):
    """A single request parameter and its related response properties."""

    request_param: str = Field(description="Name of the request parameter")

    response_properties: list[str] = Field(
        default_factory=list,
        description="List of response property paths constrained by this request parameter",
    )


class RequestResponseConstraintValidation(BaseModel):
    """Validation result from LLM indicating which request-response pairs have constraints.

    Structure: {
        "request_param_name": {
            "response_property_path": true/false
        }
    }
    """

    constraints: dict[str, dict[str, bool]] = Field(
        description="Nested mapping from request parameter to response properties with constraint indicator"
    )


class RequestResponseConstraintValidationV2(BaseModel):
    """Validation result from LLM indicating request-response constraint pairs.

    Optimized format: only list pairs that HAVE constraints (no false values).
    """

    request_response_pairs: list[RequestResponsePair] = Field(
        default_factory=list,
        description="List of request parameters and their constrained response properties",
    )


class RequestResponseConstraintOutput(BaseModel):
    """Final output containing validated request-response constraints with descriptions.

    Structure: {
        "request_param_name": {
            "response_property_path": "description of the constraint relationship"
        }
    }
    """

    constraints: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Nested mapping from request parameter to response properties with constraint descriptions",
    )
