"""
Pydantic models for CSV export.

Defines row models for constraint CSV reports.
"""

from pydantic import BaseModel


class ConstraintCSVRow(BaseModel):
    """Row model for constraint CSV export with detailed columns."""

    operation_id: str
    field_path: str
    selector_expr: str
    predicate_kind: str
    predicate_version: str
    args: str  # JSON string
    source_kind: str
    confidence: float
    evidence: str  # Truncated to 200 chars
    constraint_id: str


__all__ = ["ConstraintCSVRow"]
