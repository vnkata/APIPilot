from dataclasses import Field, dataclass, field
from pydantic import BaseModel, ConfigDict, RootModel
from typing import Any, Dict, List, Optional

# class MappingContents(RootModel):
#     root: Dict[str, Any]

class SemanticOracleJudgeSchemas(BaseModel):
    idx: int
    parameters: Optional[Dict[str, Any]] = None
    requestBody: Optional[Dict[str, Any]] = None  # only include if not None
    expected_code: str
    satisfies: bool

@dataclass
class Verdict(BaseModel):
    datas: List[SemanticOracleJudgeSchemas]
