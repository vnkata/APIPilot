"""
Typed intermediate models for constraint extraction pipeline.

Provides type-safe containers for predicates with metadata throughout
the extraction process, improving IDE support and runtime validation.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from api_testing.constraint.ir.models import PredicateModel, ProvenanceModel


class PredicateWithMetadata(BaseModel):
    """Typed container for extracted predicates with provenance.

    This is the core intermediate representation used throughout the
    extraction pipeline. It pairs a predicate (what to validate) with
    provenance (where it came from and confidence level).

    Attributes:
        predicate: The validation predicate with kind, version, and args
        provenance: Source and confidence information

    Example:
        >>> pred = PredicateWithMetadata(
        ...     predicate=PredicateModel(kind="int.range", version="v1", args={"min": 1, "max": 10}),
        ...     provenance=ProvenanceModel(kind="schema_structural", confidence=1.0, evidence="schema: minimum=1, maximum=10")
        ... )
    """

    model_config = {"frozen": False}

    predicate: PredicateModel = Field(..., description="Validation predicate")
    provenance: ProvenanceModel = Field(..., description="Source and confidence")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for compatibility with existing code.

        Returns:
            Dictionary with "predicate" and "provenance" keys containing serialized models
        """
        return {
            "predicate": self.predicate.model_dump(),
            "provenance": self.provenance.model_dump(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredicateWithMetadata":
        """Deserialize from dict.

        Args:
            data: Dictionary with "predicate" and "provenance" keys

        Returns:
            PredicateWithMetadata instance

        Raises:
            KeyError: If required keys are missing
            ValidationError: If data doesn't match model schema
        """
        return cls(
            predicate=PredicateModel(**data["predicate"]),
            provenance=ProvenanceModel(**data["provenance"]),
        )


class ExtractionResult(BaseModel):
    """Result from an extraction phase.

    Captures the outcome of a single phase (heuristic, coverage, llm)
    including predicates extracted, statistics, and any errors encountered.

    Attributes:
        predicates: List of predicates extracted in this phase
        phase: Which extraction phase produced this result
        field_path: Field being analyzed
        stats: Phase-specific statistics (counts, timings, etc.)
        errors: List of error messages encountered (for resilient handling)

    Example:
        >>> result = ExtractionResult(
        ...     predicates=[pred1, pred2],
        ...     phase="heuristic",
        ...     field_path="user.age",
        ...     stats={"structural_count": 1, "description_count": 1},
        ...     errors=[]
        ... )
    """

    model_config = {"frozen": False}

    predicates: List[PredicateWithMetadata] = Field(
        default_factory=list, description="Predicates extracted in this phase"
    )
    phase: Literal["heuristic", "coverage", "llm"] = Field(
        ...,
        description="Extraction phase: heuristic (rules), coverage (check sufficiency), llm (fill gaps)",
    )
    field_path: str = Field(..., description="Dot-notation field path")
    stats: Dict[str, Any] = Field(
        default_factory=dict, description="Phase-specific statistics and metadata"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Non-fatal errors encountered during extraction",
    )

    @property
    def success(self) -> bool:
        """Whether extraction succeeded (has predicates or no fatal errors)."""
        return len(self.predicates) > 0 or len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for intermediate output.

        Returns:
            Dictionary suitable for JSON serialization
        """
        return {
            "predicates": [p.to_dict() for p in self.predicates],
            "phase": self.phase,
            "field_path": self.field_path,
            "stats": self.stats,
            "errors": self.errors,
            "success": self.success,
        }


class CoverageCheckResult(BaseModel):
    """Result from coverage checker (Phase 2).

    Indicates whether heuristic extraction was sufficient or if
    additional constraints are needed from LLM extraction.

    Attributes:
        is_sufficient: True if heuristic constraints cover all requirements
        missing_requirements: List of constraint descriptions that weren't covered
        reasoning: Explanation of coverage assessment
        existing_summary: Summary of constraints that were found

    Example:
        >>> result = CoverageCheckResult(
        ...     is_sufficient=False,
        ...     missing_requirements=["Must validate Canadian province codes"],
        ...     reasoning="Description mentions province codes but no enum constraint found",
        ...     existing_summary="Found: int.range (1-10)"
        ... )
    """

    model_config = {"frozen": False}

    is_sufficient: bool = Field(
        ..., description="Whether existing predicates cover all requirements"
    )
    missing_requirements: List[str] = Field(
        default_factory=list,
        description="Requirements from description not yet covered",
    )
    reasoning: Optional[str] = Field(
        default=None, description="Explanation of why requirements are missing"
    )
    existing_summary: Optional[str] = Field(
        default=None, description="Summary of constraints already extracted"
    )

    @property
    def needs_llm_extraction(self) -> bool:
        """Whether LLM extraction phase is needed."""
        return not self.is_sufficient and len(self.missing_requirements) > 0


__all__ = [
    "PredicateWithMetadata",
    "ExtractionResult",
    "CoverageCheckResult",
]
