from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class FieldConfiguration:
    name: str = ""
    type: str = "" # this is the name of the Generator class
    genParameters: Dict[str, Any] = field(default_factory=dict) # parameters for the generator
@dataclass
class OperationConfiguration:
    method: str
    endpoint: str
    params: Dict[str, FieldConfiguration] = field(default_factory=dict)
    reqbody: Dict[str, FieldConfiguration] = field(default_factory=dict)