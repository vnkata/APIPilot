from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class FieldConfiguration:
    name: str = ""
    type: str = "" # this is the name of the Generator class
    genParameters: Dict[str, Any] = field(default_factory=dict) # parameters for the generator
    @classmethod
    def from_dict(cls, data: dict):
        if data is None:
            return None
        it = cls(**data)
        return it

@dataclass
class OperationConfiguration:
    method: str
    endpoint: str
    params: Dict[str, FieldConfiguration] = field(default_factory=dict)
    request_body: Dict[str, FieldConfiguration] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict):
        if data is None:
            return None
        it = cls(**data)
        if data.get("params"):
            it.params = { k: FieldConfiguration.from_dict(v) for k, v in data.get("params").items() }
        if data.get("request_body"):
            it.request_body = { k: FieldConfiguration.from_dict(v) for k,v in data.get("request_body").items() }
        return it