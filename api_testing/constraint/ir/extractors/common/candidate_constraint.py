"""
Candidate constraint model for pre-IR constraint representation.

Represents constraints before they are converted to the final IR format,
allowing for scoring, merging, and deduplication.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    pass


class Evidence(BaseModel):
    """Evidence supporting a constraint candidate.

    Tracks where the constraint came from and why it was extracted.
    """

    source: str = Field(
        ..., description="Source of evidence (schema, description, heuristic, llm)"
    )
    location: str = Field(
        ...,
        description="Specific location in source (e.g., 'parameter.userId.description')",
    )
    snippet: str | None = Field(None, description="Relevant text snippet")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score for this evidence"
    )


class CandidateConstraint(BaseModel):
    """A candidate constraint before conversion to IR.

    Represents a potential constraint with evidence, confidence scoring,
    and metadata for deduplication and merging.
    """

    # Core constraint definition
    predicate_kind: str = Field(
        ..., description="Predicate kind (e.g., 'comparison.equals', 'forall_eq')"
    )
    predicate_version: str = Field(default="v1", description="Predicate version")
    predicate_args: dict[str, Any] = Field(
        default_factory=dict, description="Predicate arguments"
    )

    # Selectors
    selectors: list[str] = Field(
        default_factory=list,
        description="Selector expressions (JSONPath, request_ref, response_ref)",
    )
    selector_types: list[str] = Field(
        default_factory=list,
        description="Selector types (jsonpath, request_ref, response_ref)",
    )

    # Scope
    operation_id: str = Field(
        ..., description="Operation UUID this constraint applies to"
    )
    phase: str = Field(default="response", description="Phase: request or response")
    location: str = Field(
        default="body", description="Location: body, header, status, etc."
    )

    # Single-field specific (optional for backwards compatibility)
    field_path: str | None = Field(
        default=None,
        description="Dot-notation field path for single-field constraints",
    )

    # Evidence and confidence
    evidence: list[Evidence] = Field(
        default_factory=list, description="Evidence supporting this constraint"
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall confidence score"
    )

    # Metadata
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization (e.g., 'filter', 'pagination')",
    )
    extractor_name: str = Field(
        ..., description="Name of extractor that created this candidate"
    )
    extracted_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Extraction timestamp",
    )

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @classmethod
    def from_single_field(
        cls,
        field_path: str,
        predicate_kind: str,
        predicate_args: dict[str, Any],
        operation_id: str,
        extractor_name: str,
        evidence_source: str,
        evidence_snippet: str,
        confidence: float = 1.0,
        predicate_version: str = "v1",
        tags: list[str] | None = None,
        array_paths: list[str] | None = None,
    ) -> "CandidateConstraint":
        """Factory method for creating single-field constraints.

        Args:
            field_path: Dot-notation field path (e.g., 'holidays.provinces.id')
            predicate_kind: Predicate kind (e.g., 'string.enum')
            predicate_args: Predicate arguments
            operation_id: Operation UUID
            extractor_name: Name of the extractor
            evidence_source: Source of evidence (schema, description, llm)
            evidence_snippet: Evidence text snippet
            confidence: Confidence score (0.0-1.0)
            predicate_version: Predicate version (default: v1)
            tags: Optional tags for categorization
            array_paths: Optional list of array paths for JSONPath conversion

        Returns:
            CandidateConstraint instance
        """
        from api_testing.validation.selectors import convert_to_jsonpath_with_arrays

        # Convert field_path to JSONPath selector
        # Convert list to set for convert_to_jsonpath_with_arrays
        jsonpath_selector = convert_to_jsonpath_with_arrays(
            field_path, set(array_paths or [])
        )

        return cls(
            predicate_kind=predicate_kind,
            predicate_version=predicate_version,
            predicate_args=predicate_args,
            selectors=[jsonpath_selector],
            selector_types=["jsonpath"],
            operation_id=operation_id,
            phase="response",
            location="body",
            field_path=field_path,
            evidence=[
                Evidence(
                    source=evidence_source,
                    location=f"schema.{field_path}",
                    snippet=evidence_snippet,
                    confidence=confidence,
                )
            ],
            confidence=confidence,
            tags=tags or [],
            extractor_name=extractor_name,
        )

    def add_evidence(
        self,
        source: str,
        location: str,
        snippet: str | None = None,
        confidence: float = 1.0,
    ):
        """Add evidence to this candidate.

        Args:
            source: Evidence source
            location: Specific location
            snippet: Text snippet
            confidence: Confidence score for this evidence
        """
        self.evidence.append(
            Evidence(
                source=source, location=location, snippet=snippet, confidence=confidence
            )
        )
        # Recalculate overall confidence
        self._recalculate_confidence()

    def _recalculate_confidence(self):
        """Recalculate overall confidence based on evidence."""
        if not self.evidence:
            self.confidence = 0.0
            return

        # Take maximum confidence from evidence, weighted by source
        source_weights = {
            "schema": 1.0,
            "heuristic": 0.9,
            "description": 0.8,
            "llm": 0.7,
            "observation": 0.85,
        }

        weighted_scores = []
        for ev in self.evidence:
            weight = source_weights.get(ev.source, 0.5)
            weighted_scores.append(ev.confidence * weight)

        # Use max score (most confident evidence)
        self.confidence = max(weighted_scores) if weighted_scores else 0.0

    def canonical_key(self) -> str:
        """Generate a canonical key for deduplication.

        Returns:
            String key that uniquely identifies this constraint
        """
        # Sort selectors for consistent ordering
        sorted_selectors = sorted(self.selectors)

        # Normalize predicate args for comparison
        args_str = str(sorted(self.predicate_args.items()))

        # Include field_path if present for single-field constraints
        field_part = f":{self.field_path}" if self.field_path else ""

        return f"{self.operation_id}:{self.predicate_kind}@{self.predicate_version}:{','.join(sorted_selectors)}:{args_str}{field_part}"

    def merge_with(self, other: "CandidateConstraint"):
        """Merge another candidate into this one.

        Combines evidence and takes the higher confidence.

        Args:
            other: Another CandidateConstraint to merge
        """
        # Merge evidence
        for ev in other.evidence:
            # Avoid duplicate evidence
            if not any(
                e.source == ev.source and e.location == ev.location
                for e in self.evidence
            ):
                self.evidence.append(ev)

        # Merge tags
        for tag in other.tags:
            if tag not in self.tags:
                self.tags.append(tag)

        # Merge metadata
        self.metadata.update(other.metadata)

        # Recalculate confidence
        self._recalculate_confidence()

    def to_constraint_model(self):
        """Convert to ConstraintModel for final IR.

        Returns:
            ConstraintModel instance
        """
        from api_testing.constraint.ir.core import (
            ConstraintModel,
            PredicateModel,
            ProvenanceModel,
            ScopeModel,
            SelectorModel,
        )

        # Build selectors
        selector_models = []
        for i, selector_expr in enumerate(self.selectors):
            selector_type = (
                self.selector_types[i] if i < len(self.selector_types) else "jsonpath"
            )
            selector_models.append(
                SelectorModel(kind=selector_type, expr=selector_expr, mode="all")
            )

        # Build provenance
        provenance_kind = "schema_structural"
        if self.evidence:
            # Use most confident evidence source
            best_evidence = max(self.evidence, key=lambda e: e.confidence)
            source_map = {
                "schema": "schema_structural",
                "description": "schema_description",
                "heuristic": "schema_structural",
                "llm": "llm",
                "observation": "observed_payload",
            }
            provenance_kind = source_map.get(best_evidence.source, "llm")

        provenance = ProvenanceModel(
            kind=provenance_kind,
            confidence=self.confidence,
            evidence="; ".join(
                f"{e.source}:{e.location}" for e in self.evidence[:3]
            ),  # First 3 evidence
            extracted_at=self.extracted_at,
        )

        # Build metadata with field_path if present
        constraint_metadata = {
            "tags": self.tags,
            "extractor": self.extractor_name,
            **self.metadata,
        }
        if self.field_path:
            constraint_metadata["field_path"] = self.field_path

        # Build unique constraint ID
        constraint_id_parts = [self.operation_id, self.predicate_kind.replace(".", "_")]
        if self.field_path:
            constraint_id_parts.append(self.field_path.replace(".", "_"))
        constraint_id = ".".join(constraint_id_parts)

        # Build constraint
        constraint = ConstraintModel(
            id=constraint_id,
            scope=ScopeModel(
                operation=self.operation_id,
                phase=self.phase,
                location=self.location,
            ),
            selectors=selector_models,
            predicates=[
                PredicateModel(
                    kind=self.predicate_kind,
                    version=self.predicate_version,
                    args=self.predicate_args,
                )
            ],
            severity="error" if self.confidence > 0.7 else "warn",
            source=provenance,
            metadata=constraint_metadata,
        )

        return constraint


__all__ = ["Evidence", "CandidateConstraint"]
