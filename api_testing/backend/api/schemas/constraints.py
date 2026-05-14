from __future__ import annotations

from pydantic import Field, JsonValue

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    GroupCountResponse,
    PaginationMetadata,
)
from api_testing.backend.domain.models import (
    ConstraintEntry,
    ConstraintEntryDetail,
    ConstraintSection,
    DynamicConstraints,
    GroupedPage,
    InvariantDetail,
    InvariantGroup,
    InvariantRecord,
    StaticConstraints,
)


class ConstraintEntryResponse(BackendBaseModel):
    operation_id: str
    property_path: str
    expression: str

    @classmethod
    def from_domain(cls, entry: ConstraintEntry) -> "ConstraintEntryResponse":
        return cls(
            operation_id=entry.operation_id,
            property_path=entry.property_path,
            expression=entry.expression,
        )


class ConstraintEntryDetailResponse(ConstraintEntryResponse):
    section: str | None = None

    @classmethod
    def from_domain(
        cls, entry: ConstraintEntryDetail
    ) -> "ConstraintEntryDetailResponse":
        return cls(
            operation_id=entry.operation_id,
            property_path=entry.property_path,
            expression=entry.expression,
            section=entry.section,
        )


class ConstraintEntryPageResponse(BackendBaseModel):
    run_name: str
    items: list[ConstraintEntryDetailResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: GroupedPage[ConstraintEntryDetail],
    ) -> "ConstraintEntryPageResponse":
        return cls(
            run_name=run_name,
            items=[ConstraintEntryDetailResponse.from_domain(item) for item in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )


class ConstraintSectionResponse(BackendBaseModel):
    name: str
    constraints: list[ConstraintEntryResponse]

    @classmethod
    def from_domain(
        cls, section: ConstraintSection
    ) -> "ConstraintSectionResponse":
        return cls(
            name=section.name,
            constraints=[
                ConstraintEntryResponse.from_domain(entry)
                for entry in section.constraints
            ],
        )


class StaticConstraintsResponse(BackendBaseModel):
    run_name: str
    sections: list[ConstraintSectionResponse]
    constraint_count: int = Field(ge=0)

    @classmethod
    def from_domain(
        cls, constraints: StaticConstraints
    ) -> "StaticConstraintsResponse":
        return cls(
            run_name=constraints.run_name,
            sections=[
                ConstraintSectionResponse.from_domain(section)
                for section in constraints.sections
            ],
            constraint_count=constraints.constraint_count,
        )


class InvariantRecordResponse(BackendBaseModel):
    pptname: str | None = None
    invariant: str | None = None
    invariant_type: str | None = None
    variables: str | None = None
    postman_assertion: str | None = None

    @classmethod
    def from_domain(cls, invariant: InvariantRecord) -> "InvariantRecordResponse":
        return cls(
            pptname=invariant.pptname,
            invariant=invariant.invariant,
            invariant_type=invariant.invariant_type,
            variables=invariant.variables,
            postman_assertion=invariant.postman_assertion,
        )


class InvariantDetailResponse(BackendBaseModel):
    operation_id: str | None = None
    pptname: str | None = None
    invariant: str | None = None
    invariant_type: str | None = None
    variables: str | None = None
    postman_assertion: str | None = None

    @classmethod
    def from_domain(cls, invariant: InvariantDetail) -> "InvariantDetailResponse":
        return cls(
            operation_id=invariant.operation_id,
            pptname=invariant.pptname,
            invariant=invariant.invariant,
            invariant_type=invariant.invariant_type,
            variables=invariant.variables,
            postman_assertion=invariant.postman_assertion,
        )


class InvariantPageResponse(BackendBaseModel):
    run_name: str
    items: list[InvariantDetailResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: GroupedPage[InvariantDetail],
    ) -> "InvariantPageResponse":
        return cls(
            run_name=run_name,
            items=[InvariantDetailResponse.from_domain(item) for item in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )


class InvariantGroupResponse(BackendBaseModel):
    operation_id: str
    invariants: list[JsonValue]

    @classmethod
    def from_domain(cls, group: InvariantGroup) -> "InvariantGroupResponse":
        return cls(operation_id=group.operation_id, invariants=group.invariants)


class DynamicConstraintsResponse(BackendBaseModel):
    run_name: str
    constraints: list[ConstraintEntryResponse]
    groups: list[InvariantGroupResponse]
    invariants: list[InvariantRecordResponse]
    constraint_count: int = Field(ge=0)
    invariant_count: int = Field(ge=0)

    @classmethod
    def from_domain(
        cls, constraints: DynamicConstraints
    ) -> "DynamicConstraintsResponse":
        return cls(
            run_name=constraints.run_name,
            constraints=[
                ConstraintEntryResponse.from_domain(entry)
                for entry in constraints.constraints
            ],
            groups=[
                InvariantGroupResponse.from_domain(group)
                for group in constraints.groups
            ],
            invariants=[
                InvariantRecordResponse.from_domain(invariant)
                for invariant in constraints.invariants
            ],
            constraint_count=constraints.constraint_count,
            invariant_count=constraints.invariant_count,
        )
