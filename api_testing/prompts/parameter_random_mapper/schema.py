from pydantic import BaseModel, Field
from typing import Any, Dict, List

class GenContent(BaseModel):
    className: str
    args: Dict[str, Any]

class PropertyGenContent(BaseModel):
    property: str
    generator: GenContent

class Verdict(BaseModel):
    mapping: List[PropertyGenContent]
