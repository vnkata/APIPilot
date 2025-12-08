from dataclasses import dataclass
from pydantic import BaseModel
from typing import List


@dataclass
class ReqResConstraintVerdict(BaseModel):
    parameter: str
    description: str
    property: str

    def to_dict(self):
        return {
            "parameter": self.parameter,
            "description": self.description,
            "property": self.property
        }


@dataclass
class Verdict(BaseModel):
    constraint: List[ReqResConstraintVerdict]

    def to_dict(self):
        return {
            "constraint":  [item.to_dict() for item in self.constraint]
        }
