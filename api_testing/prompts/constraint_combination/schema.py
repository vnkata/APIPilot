from typing import Literal

from pydantic import BaseModel, ConfigDict


class ConstraintCombinationVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relation: Literal[
        "EQUIVALENT",
        "STATIC_STRONGER",
        "DYNAMIC_STRONGER",
        "PARTIAL_OVERLAP",
        "DISJOINT",
        "UNKNOWN",
    ]
    reason: str
