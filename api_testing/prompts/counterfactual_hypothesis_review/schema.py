from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class BestHypothesis(str, Enum):
    hypothesis_1 = "hypothesis_1"
    hypothesis_2 = "hypothesis_2"
    equal = "equal"
    union = "union"


class CounterfactualHypothesisReviewResult(BaseModel):
    id: int
    best_hypothesis: BestHypothesis
    explanation: str = Field(..., description="Short reasoning about which hypothesis is more consistent with the counterexamples")


class Verdict(BaseModel):
    datas: List[CounterfactualHypothesisReviewResult]
