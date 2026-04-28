from pydantic import BaseModel
from typing import List, Optional

class ReqResConstraintVerdict(BaseModel):
    parameter: Optional[str] = None
    predicate: str
    property: Optional[str] = None


class Verdict(BaseModel):
    constraints: List[ReqResConstraintVerdict]
