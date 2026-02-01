"""
Predicate registry models and schemas.

Defines metadata for all validator primitives including:
- Arguments schema
- Supported types
- Description and examples
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class PredicateArgsSchema(BaseModel):
    """JSON Schema for predicate arguments validation."""

    model_config = ConfigDict(frozen=True, extra="allow")

    type: str = Field(default="object")
    required: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    additionalProperties: bool = Field(default=False)


class PredicateMetadata(BaseModel):
    """Metadata for a single validator predicate.

    Defines the predicate's interface, validation logic, and usage information.
    """

    model_config = ConfigDict(frozen=True)

    kind: str = Field(..., description="Predicate kind (e.g., 'int.range')")
    version: str = Field(..., pattern=r"^v\d+$", description="Predicate version")
    category: Literal[
        "integer",
        "string",
        "number",
        "boolean",
        "date",
        "array",
        "object",
        "cross-field",
        "comparison",
        "request-response",
    ] = Field(..., description="Predicate category")
    description: str = Field(..., description="Human-readable description")
    args_schema: PredicateArgsSchema = Field(
        ..., description="JSON Schema for arguments"
    )
    supported_types: list[str] = Field(
        ..., description="Supported value types (e.g., ['integer', 'number'])"
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list, description="Usage examples with args and test values"
    )
    implemented: bool = Field(
        default=False, description="Whether validator function is implemented"
    )

    @property
    def ref(self) -> str:
        """Full predicate reference (kind@version)."""
        return f"{self.kind}@{self.version}"


class PredicateRegistry(BaseModel):
    """Complete registry of predicate metadata."""

    model_config = ConfigDict(frozen=False)

    version: str = Field(default="1.0", description="Registry version")
    predicates: list[PredicateMetadata] = Field(
        default_factory=list, description="List of predicate metadata"
    )

    def get(self, kind: str, version: str = "v1") -> PredicateMetadata | None:
        """Get predicate metadata by kind and version."""
        ref = f"{kind}@{version}"
        for p in self.predicates:
            if p.ref == ref:
                return p
        return None

    def list_implemented(self) -> list[PredicateMetadata]:
        """Get all implemented predicates."""
        return [p for p in self.predicates if p.implemented]

    def list_by_category(self, category: str) -> list[PredicateMetadata]:
        """Get predicates by category."""
        return [p for p in self.predicates if p.category == category]


class ProposedPredicateModel(BaseModel):
    """Model for LLM-proposed predicate definitions."""

    model_config = ConfigDict(frozen=False)

    kind: str = Field(..., description="Predicate kind (e.g., 'date.before_field')")
    version: str = Field(..., pattern=r"^v\d+$", description="Predicate version")
    category: Literal[
        "integer",
        "string",
        "number",
        "boolean",
        "date",
        "array",
        "object",
        "cross-field",
        "comparison",
        "request-response",
    ] = Field(..., description="Predicate category")
    description: str = Field(..., description="Human-readable description")
    args_schema: PredicateArgsSchema = Field(
        ..., description="JSON Schema for arguments"
    )
    proposed_by: Literal["llm", "manual"] = Field(
        default="llm", description="Source of proposal"
    )
    evidence: str = Field(..., description="Context/reasoning for this proposal")
    status: Literal["pending_review", "approved", "rejected"] = Field(
        default="pending_review", description="Review status"
    )
    proposed_at: str = Field(..., description="ISO timestamp of proposal")
    field_context: str | None = Field(
        default=None, description="Field path this was proposed for"
    )


class ProposedPredicateRegistry(BaseModel):
    """Registry of LLM-proposed predicates."""

    model_config = ConfigDict(frozen=False)

    version: str = Field(default="1.0", description="Registry version")
    predicates: list[ProposedPredicateModel] = Field(
        default_factory=list, description="List of proposed predicates"
    )


__all__ = [
    "PredicateArgsSchema",
    "PredicateMetadata",
    "PredicateRegistry",
    "ProposedPredicateModel",
    "ProposedPredicateRegistry",
]
