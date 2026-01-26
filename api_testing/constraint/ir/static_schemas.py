"""Shared Pydantic models for static constraint data structures.

These models are used by both StaticConstraintMiner (for output)
and ConstraintIRBuilder (for input parsing).
"""

from typing import Dict, Optional, Any
from pydantic import BaseModel, Field


class OperationConstraintsData(BaseModel):
    """Unified constraints data for a single operation.

    Contains both response property constraints and request-response constraints,
    plus the new unified constraints structure.
    """

    response_properties_constraints: Dict[str, str] = Field(
        default_factory=dict,
        description="Maps response property paths to constraint descriptions (legacy)",
    )

    request_response_constraints: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Maps request parameters to response properties with constraint descriptions (legacy)",
    )

    constraints: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Unified constraint structure with body and detail sections",
    )


class StaticConstraintMinerOutput(BaseModel):
    """Complete output from StaticConstraintMiner.

    Groups all constraints by operation UUID, with each operation containing
    both response property constraints and request-response constraints.
    """

    operations: Dict[str, OperationConstraintsData] = Field(
        default_factory=dict,
        description="Maps operation UUIDs to their constraint data",
    )


__all__ = ["OperationConstraintsData", "StaticConstraintMinerOutput"]
