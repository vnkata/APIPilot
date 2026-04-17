
from pydantic import BaseModel
from typing import Dict

class Verdict(BaseModel):
    constraints: Dict[str, str]