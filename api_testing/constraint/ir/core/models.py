"""
Enhanced Constraint IR models with Scope, Provenance, and Conditions.

Implements the complete IR v2 architecture as per CONSTRAINTS_TO_IR_TO_ENGINE_PROPOSAL.md.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Selector Models
# ============================================================================


class SelectorModel(BaseModel):
    """Selector for extracting values from request/response data.

    Supports multiple selector types:
    - jsonpath: RFC 9535 JSONPath for response body
    - request_ref: Reference to request parts (path/query/header/body)
    - response_ref: Reference to response parts (status/header/body)
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal["jsonpath", "request_ref", "response_ref"] = Field(
        ..., description="Selector type"
    )
    expr: str = Field(
        ..., description="Selector expression (JSONPath or reference path)"
    )
    mode: Literal["all", "any", "first"] = Field(
        default="all",
        description="How to handle multiple matches: all (validate all), any (at least one valid), first (validate only first)",
    )


# ============================================================================
# Condition Models
# ============================================================================


class ConditionModel(BaseModel):
    """Conditional constraint application using CEL expressions.

    Allows constraints to be applied only when certain conditions are met.
    Example: Apply constraint only when status_code==200
    """

    model_config = ConfigDict(frozen=True)

    lang: Literal["cel", "python"] = Field(
        default="cel", description="Expression language (cel recommended)"
    )
    expr: str = Field(
        ..., description="Condition expression that must evaluate to boolean"
    )


# ============================================================================
# Provenance Models
# ============================================================================


class ProvenanceModel(BaseModel):
    """Tracks the source and confidence of a constraint.

    Essential for understanding where constraints come from and
    for filtering/prioritizing constraints by confidence.
    """

    model_config = ConfigDict(frozen=True)

    kind: Literal[
        "schema_structural",
        "schema_description",
        "observed_payload",
        "llm",
        "manual",
        "merged",
    ] = Field(..., description="Source of the constraint")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    evidence: str | None = Field(
        default=None,
        description="Evidence supporting this constraint (e.g., spec snippet, observation count)",
    )
    extracted_at: str | None = Field(
        default=None, description="ISO timestamp when constraint was extracted"
    )


# ============================================================================
# Scope Models
# ============================================================================


class ScopeModel(BaseModel):
    """Defines the scope where a constraint applies.

    Specifies the operation, phase (request/response), and location
    within that phase where validation should occur.
    """

    model_config = ConfigDict(frozen=True)

    operation: str = Field(
        ..., description="Operation identifier (e.g., 'get-/api/v1/holidays')"
    )
    phase: Literal["request", "response"] = Field(
        ..., description="Request or response validation"
    )
    location: Literal["body", "query", "path", "header"] | None = Field(
        default=None, description="Specific location within phase (optional for body)"
    )


# ============================================================================
# Predicate Models
# ============================================================================


class PredicateModel(BaseModel):
    """Reference to a validation predicate with arguments.

    Points to a versioned validator primitive in the registry.
    """

    model_config = ConfigDict(frozen=False)

    kind: str = Field(
        ..., description="Validator kind (e.g., 'int.range', 'string.enum')"
    )
    version: str = Field(
        ..., pattern=r"^v\d+$", description="Validator version (e.g., 'v1')"
    )
    args: dict[str, Any] = Field(
        default_factory=dict, description="Validator-specific arguments"
    )

    @property
    def ref(self) -> str:
        """Full predicate reference (kind@version)."""
        return f"{self.kind}@{self.version}"

    def to_human_readable(self) -> str:
        """Convert predicate to natural language description.

        Returns:
            Human-readable constraint description suitable for LLM prompts

        Examples:
            - int.range@v1 {min: 1, max: 100} -> "must be between 1 and 100"
            - string.pattern@v1 {pattern: "^[A-Z]"} -> "must match pattern '^[A-Z]'"
            - string.enum@v1 {values: ["A", "B"]} -> "must be one of: A, B"
        """
        # Parse predicate components
        parts = self.kind.split(".")
        category = parts[0] if len(parts) > 0 else "unknown"
        name = parts[1] if len(parts) > 1 else self.kind

        # Format based on common predicate types
        if category == "int" or category == "number":
            if name == "range":
                min_val = self.args.get("min", "?")
                max_val = self.args.get("max", "?")
                return f"must be between {min_val} and {max_val}"
            elif name == "min":
                return f"must be >= {self.args.get('value', '?')}"
            elif name == "max":
                return f"must be <= {self.args.get('value', '?')}"

        elif category == "string":
            if name == "pattern":
                pattern = self.args.get("pattern", "?")
                return f"must match pattern '{pattern}'"
            elif name == "enum" or name == "one_of":
                values = self.args.get("values", [])
                if values:
                    values_str = ", ".join(str(v) for v in values[:5])
                    if len(values) > 5:
                        values_str += f", ... ({len(values)} total)"
                    return f"must be one of: {values_str}"
                return "must be from allowed set"
            elif name == "length":
                min_len = self.args.get("min")
                max_len = self.args.get("max")
                if min_len and max_len:
                    return f"length must be between {min_len} and {max_len}"
                elif min_len:
                    return f"length must be >= {min_len}"
                elif max_len:
                    return f"length must be <= {max_len}"
            elif name == "format":
                fmt = self.args.get("format", "?")
                return f"must be valid {fmt} format"

        elif category == "date":
            if name == "range":
                return "must be within date range"
            elif name == "before":
                return "must be before specified date"
            elif name == "after":
                return "must be after specified date"

        elif category == "boolean":
            if name == "is_true":
                return "must be true"
            elif name == "is_false":
                return "must be false"

        elif category == "array":
            if name == "length":
                min_len = self.args.get("min")
                max_len = self.args.get("max")
                if min_len and max_len:
                    return f"array length must be between {min_len} and {max_len}"
                elif min_len:
                    return f"array length must be >= {min_len}"
                elif max_len:
                    return f"array length must be <= {max_len}"
            elif name == "unique":
                return "array items must be unique"

        elif category == "comparison":
            if name == "equals":
                return "must be equal to"
            elif name == "lt":
                return "must be less than"
            elif name == "gt":
                return "must be greater than"

        # Fallback: structured format
        if self.args:
            args_str = ", ".join(f"{k}={v}" for k, v in self.args.items())
            return f"{self.kind}({args_str})"
        return self.kind


# ============================================================================
# Constraint Models
# ============================================================================


class ConstraintModel(BaseModel):
    """Single constraint definition with full metadata.

    Core unit of the IR - defines what to validate, where, and how.
    """

    model_config = ConfigDict(frozen=False)

    id: str = Field(..., description="Unique constraint identifier")
    scope: ScopeModel = Field(..., description="Where this constraint applies")
    selectors: list[SelectorModel] = Field(
        min_length=1,
        description="Value selectors (can be multiple for cross-field constraints)",
    )
    predicates: list[PredicateModel] = Field(
        min_length=1, description="Validation predicates to apply"
    )
    when: ConditionModel | None = Field(
        default=None, description="Optional condition for applying constraint"
    )
    severity: Literal["error", "warn", "info"] = Field(
        default="error", description="Violation severity"
    )
    source: ProvenanceModel = Field(..., description="Provenance information")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def to_human_readable(self) -> str:
        """Convert entire constraint to human-readable format.

        Returns:
            Natural language description of constraint

        Example:
            "Field $.items[*].price must be between 1 and 1000
            (source: schema_structural, confidence: 1.0)"
        """
        # Format selectors
        if len(self.selectors) == 1:
            selector_str = f"Field {self.selectors[0].expr}"
        else:
            selector_exprs = [s.expr for s in self.selectors]
            selector_str = f"Fields {', '.join(selector_exprs)}"

        # Format predicates
        predicate_descriptions = [p.to_human_readable() for p in self.predicates]
        if len(predicate_descriptions) == 1:
            predicate_str = predicate_descriptions[0]
        else:
            predicate_str = " AND ".join(predicate_descriptions)

        # Format source and confidence
        source_str = (
            f"(source: {self.source.kind}, confidence: {self.source.confidence:.2f})"
        )

        # Add condition if present
        if self.when:
            return f"{selector_str} {predicate_str} when {self.when.expr} {source_str}"
        else:
            return f"{selector_str} {predicate_str} {source_str}"


# ============================================================================
# Operation Models
# ============================================================================


class OperationConstraintsModel(BaseModel):
    """All constraints for a single API operation."""

    model_config = ConfigDict(frozen=False)

    constraints: list[ConstraintModel] = Field(
        default_factory=list, description="List of constraints for this operation"
    )


# ============================================================================
# Top-Level IR Models
# ============================================================================


class ConstraintIRModel(BaseModel):
    """Complete Constraint IR document (v2).

    Top-level model containing all operation constraints with
    full scope, provenance, and conditional support.
    """

    model_config = ConfigDict(frozen=False)

    version: str = Field(default="v2", description="IR schema version")
    operation_constraints: dict[str, OperationConstraintsModel] = Field(
        default_factory=dict, description="Map of operation ID to constraints"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Document-level metadata (tool version, created_at, etc.)",
    )


# ============================================================================
# Validation Result Models
# ============================================================================


class ViolationModel(BaseModel):
    """Validation violation result."""

    model_config = ConfigDict(frozen=False)

    constraint_id: str = Field(..., description="ID of violated constraint")
    predicate_ref: str = Field(..., description="Predicate reference (kind@version)")
    message: str = Field(..., description="Human-readable error message")
    path: str = Field(..., description="Path to violated field")
    value: Any = Field(..., description="Actual value that violated constraint")
    expected: Any | None = Field(
        default=None, description="Expected value or constraint"
    )
    severity: Literal["error", "warn", "info"] = Field(
        default="error", description="Violation severity"
    )


class ValidationResultModel(BaseModel):
    """Complete validation result for an operation."""

    model_config = ConfigDict(frozen=False)

    operation_id: str = Field(..., description="Operation that was validated")
    violations: list[ViolationModel] = Field(
        default_factory=list, description="List of violations found"
    )
    constraints_evaluated: int = Field(
        default=0, description="Number of constraints evaluated"
    )
    passed: int = Field(default=0, description="Number of constraints passed")
    failed: int = Field(default=0, description="Number of constraints failed")
    skipped: int = Field(
        default=0, description="Number of constraints skipped (conditions not met)"
    )


__all__ = [
    "SelectorModel",
    "ConditionModel",
    "ProvenanceModel",
    "ScopeModel",
    "PredicateModel",
    "ConstraintModel",
    "OperationConstraintsModel",
    "ConstraintIRModel",
    "ViolationModel",
    "ValidationResultModel",
]
