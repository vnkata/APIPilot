from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from api_testing.constraint.dynamic_constraints.invariant_reader import InvariantRecord
from api_testing.models.specification_model import OperationProperties


@dataclass(frozen=True, slots=True)
class PathSegment:
    name: str | None
    is_array: bool = False

    def display(self) -> str:
        if self.name is None:
            return "[]" if self.is_array else ""
        return f"{self.name}[]" if self.is_array else self.name


@dataclass(frozen=True, slots=True)
class VariableReference:
    raw: str
    role: str
    is_size: bool
    path_segments: tuple[PathSegment, ...]
    display_path: str


@dataclass(frozen=True, slots=True)
class ParsedProgramPoint:
    raw: str
    operation_key: str
    http_method: str
    endpoint_path: str
    status_code: str
    program_point: str
    container_segments: tuple[PathSegment, ...]

    @property
    def response_container_path(self) -> str:
        display = ".".join(
            segment.display() for segment in self.container_segments if segment.display()
        )
        return display or "<root>"


@dataclass(frozen=True, slots=True)
class NormalizedInvariantContext:
    record: InvariantRecord
    parsed_program_point: ParsedProgramPoint
    operation: OperationProperties
    invariant_description: str
    input_variables: tuple[VariableReference, ...]
    output_variables: tuple[VariableReference, ...]


@dataclass(frozen=True, slots=True)
class SchemaEntry:
    path: str
    tokens: tuple[str, ...]
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)


InvariantExcerptShape = Literal[
    "simple_scalar",
    "nested_object",
    "array_focused",
    "mixed_container_scalar",
]


@dataclass(frozen=True, slots=True)
class ExcerptBudgetProfile:
    max_request_lines: int
    max_response_lines: int
    max_container_fields: int
    max_fallback_paths: int


@dataclass(frozen=True, slots=True)
class ExcerptLine:
    source: str
    path: str
    kind: str
    line: str
    match_score: int
    is_container: bool
    path_depth: int


@dataclass(frozen=True, slots=True)
class MatchedSchemaPath:
    """A schema entry that was actually rendered into a spec excerpt."""

    source: str
    path: str
    kind: str
    match_score: int


@dataclass(frozen=True, slots=True)
class ExcerptBuildResult:
    """Specification excerpt plus the compact debug metadata used to build it."""

    excerpt: str
    shape: InvariantExcerptShape
    budget_profile: ExcerptBudgetProfile
    matched_schema_paths: tuple[MatchedSchemaPath, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class SchemaIndex:
    arrays: dict[str, SchemaEntry] = field(default_factory=dict)
    objects: dict[str, SchemaEntry] = field(default_factory=dict)
    leaves: dict[str, SchemaEntry] = field(default_factory=dict)

    def merge(self, other: "SchemaIndex") -> "SchemaIndex":
        self.arrays.update(other.arrays)
        self.objects.update(other.objects)
        self.leaves.update(other.leaves)
        return self

    def available_paths(self, limit: int = 8) -> list[str]:
        ordered_paths = list(self.arrays.keys()) + list(self.objects.keys()) + [
            path
            for path in self.leaves.keys()
            if path not in self.arrays and path not in self.objects
        ]
        return sorted(ordered_paths)[:limit]
