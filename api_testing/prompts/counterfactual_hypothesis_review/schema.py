from __future__ import annotations

from enum import Enum, IntEnum
from typing import List, Literal

from pydantic import BaseModel, Field, RootModel


# class BestHypothesis(str, Enum):
#     hypothesis_1 = "hypothesis_1"
#     hypothesis_2 = "hypothesis_2"
#     equal = "equal"
#     union = "union"


# class CounterfactualHypothesisReviewResult(BaseModel):
#     id: int
#     best_hypothesis: BestHypothesis
#     explanation: str = Field(..., description="Short reasoning about which hypothesis is more consistent with the counterexamples")


# class Verdict(BaseModel):
#     datas: List[CounterfactualHypothesisReviewResult]

class VerdictType(IntEnum):
    HYPOTHESIS_1 = 1
    HYPOTHESIS_2 = 2
    UNION = 3

class Verdict(RootModel[VerdictType]):
    @property
    def label(self):
        return {
            VerdictType.HYPOTHESIS_1: "hypothesis_1",
            VerdictType.HYPOTHESIS_2: "hypothesis_2",
            VerdictType.UNION: "union"
        }[self.root]