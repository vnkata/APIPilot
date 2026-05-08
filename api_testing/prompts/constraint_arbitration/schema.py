from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class ConstraintArbitrationResult(BaseModel):
    id: int
    answer: int


class Verdict(BaseModel):
    datas: List[ConstraintArbitrationResult]
