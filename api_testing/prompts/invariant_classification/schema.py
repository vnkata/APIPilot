from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class InvariantClassificationVerdict(str, Enum):
    TRUE_POSITIVE = "true-positive"
    FALSE_POSITIVE = "false-positive"
    INCONCLUSIVE = "inconclusive"


class InvariantClassificationResult(BaseModel):
    verdict: InvariantClassificationVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)
