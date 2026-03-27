from dataclasses import Field, dataclass, field
from pydantic import BaseModel, ConfigDict, RootModel
from typing import Any, Dict, List, Optional

class AdjustContents(BaseModel):
    invalid_resource_pair:  bool
    constraints: Optional[Dict[str, Any]] = None
    invalid_parameter_source: Optional[Dict[str, Any]] = None

@dataclass
class Verdict(BaseModel):
    datas: List[AdjustContents]
