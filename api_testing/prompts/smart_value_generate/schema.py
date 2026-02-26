from dataclasses import Field, dataclass, field
from pydantic import BaseModel, ConfigDict, RootModel
from typing import Any, Dict, List, Optional

# class MappingContents(RootModel):
#     root: Dict[str, Any]

class EndpointPayload(BaseModel):
    parameters: Optional[Dict[str, Any]] = None
    requestBody: Optional[Dict[str, Any]] = None  # only include if not None
    expected_code: str

@dataclass
class Verdict(BaseModel):
    datas: List[EndpointPayload]
