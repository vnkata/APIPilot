"""Pydantic models for request-response constraint extraction."""

from typing import Dict, List
from pydantic import BaseModel, Field
from dataclasses import dataclass


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
    constraint: List[ReqResConstraintVerdict]

    def to_dict(self):
        return {"constraint": [item.to_dict() for item in self.constraint]}


class RequestResponseConstraintValidation(BaseModel):
    """Validation result from LLM indicating which request-response pairs have constraints.

    Structure: {
        "request_param_name": {
            "response_property_path": true/false
        }
    }
    """

    constraints: Dict[str, Dict[str, bool]] = Field(
        description="Nested mapping from request parameter to response properties with constraint indicator"
    )


class RequestResponseConstraintOutput(BaseModel):
    """Final output containing validated request-response constraints with descriptions.

    Structure: {
        "request_param_name": {
            "response_property_path": "description of the constraint relationship"
        }
    }
    """

    constraints: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Nested mapping from request parameter to response properties with constraint descriptions",
    )
