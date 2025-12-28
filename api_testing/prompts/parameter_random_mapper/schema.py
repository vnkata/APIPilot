from dataclasses import Field, dataclass
from pydantic import BaseModel, ConfigDict, RootModel
from typing import Dict, List

class MappingContents(RootModel):
    root: Dict[str,str]

@dataclass
class Verdict(BaseModel):
    schemas: Dict[str, MappingContents]
