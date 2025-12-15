from dataclasses import Field, dataclass
from pydantic import BaseModel, ConfigDict
from typing import Dict, List

@dataclass
class Verdict(BaseModel):
    model_config = ConfigDict(extra='allow') # Cấu hình Pydantic v2
    schemas: Dict[str, Dict[str, str]]
    