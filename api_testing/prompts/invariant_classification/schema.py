from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Invariant(BaseModel):
    id: int
    classification: str


class Verdict(BaseModel):
    datas: List[Invariant]
