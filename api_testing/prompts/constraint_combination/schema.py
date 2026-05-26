from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class CounterExamplePlan(BaseModel):
    target_side: Literal["STATIC_TRUE_DYNAMIC_FALSE", "DYNAMIC_TRUE_STATIC_FALSE"]
    concrete_property_value: Optional[Any] = None
    staged_payload: Dict[str, Any] = Field(default_factory=dict)
    staged_payloads: List[Dict[str, Any]] = Field(default_factory=list)
    server_actual_response: Optional[Dict[str, Any]] = None


class ConstraintCombinationVerdict(BaseModel):
    status: Literal["COMBINED_EQUIVALENT", "NOT_COMBINED"]
    final_constraint: Optional[str] = None
    reason: str
    counter_example: Optional[CounterExamplePlan] = None
