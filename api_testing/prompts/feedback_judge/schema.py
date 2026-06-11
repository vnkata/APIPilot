from dataclasses import Field, dataclass, field
from pydantic import BaseModel, ConfigDict, RootModel
from typing import Any, Dict, List, Literal, Optional

class CombinationConstraintItem(BaseModel):
    type: Literal["at_least_one", "mutually_exclusive", "all_or_none", "requires"]
    params: List[str]
    description: str
    
class AdjustContents(BaseModel):
    invalid_resource_pair:  bool
    constraints: Optional[Dict[str, Any]] = None
    combination_constraints: Optional[List[CombinationConstraintItem]] = None
    invalid_parameter_source: Optional[Dict[str, Any]] = None

@dataclass
class Verdict(BaseModel):
    datas: List[AdjustContents]
