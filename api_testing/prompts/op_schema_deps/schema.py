from dataclasses import Field, dataclass
from pydantic import BaseModel
from typing import Dict, List

@dataclass
class Verdict(BaseModel):
    schemas: Dict[str, Dict[str, List[str]]]
    