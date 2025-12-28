from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class FieldConfiguration:
    name: str = ""
    type: str = ""
    genParameters: Dict[str, Any] = field(default_factory=dict)

class OperationConfiguration:
    method: str
    endpoint: str
    params: Dict[str, FieldConfiguration] = field(default_factory=dict)
    reqbody: Dict[str, FieldConfiguration] = field(default_factory=dict)