from pydantic import BaseModel, Field
from typing import Any, Dict, List

class GenContent(BaseModel):
    className: str = "LLMGenerator"
    args: Dict[str, Any] = Field(default_factory=dict)

class PropertyGenContent(BaseModel):
    idx: int
    property: str
    generator: GenContent

class Verdict(BaseModel):
    mapping: List[PropertyGenContent]
