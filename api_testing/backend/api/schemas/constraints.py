from __future__ import annotations

from pydantic import Field, JsonValue

from api_testing.backend.api.schemas.common import (
    BackendBaseModel,
    GroupCountResponse,
    PaginationMetadata,
)
from api_testing.backend.domain.models import (
    AgreementStatus,
    CombinedSource,
    CombinationDetail,
    CombinationEntry,
    CombinationEntryPage,
    CombinationFacets,
    CombinationSummary,
    ConstraintEntry,
    ConstraintEntryDetail,
    ConstraintExplorerDetail,
    ConstraintExplorerEntry,
    ConstraintExplorerPage,
    ConstraintFacetBucket,
    ConstraintFacets,
    ConstraintKind,
    ConstraintQueryMetadata,
    ConstraintSection,
    ConstraintSource,
    DynamicConstraints,
    GroupedPage,
    InvariantCorrelationEvidence,
    InvariantDetail,
    InvariantExplorerDetail,
    InvariantExplorerEntry,
    InvariantExplorerFacets,
    InvariantExplorerPage,
    InvariantGroup,
    InvariantKind,
    InvariantRecord,
    OracleReadiness,
    CorrelationConfidence,
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


class ConstraintQueryMetadataResponse(BackendBaseModel):
    combined_source: CombinedSource
    warnings: list[str]

    @classmethod
    def from_domain(
        cls, metadata: ConstraintQueryMetadata
    ) -> "ConstraintQueryMetadataResponse":
        return cls(
            combined_source=metadata.combined_source,
            warnings=metadata.warnings,
        )


class ConstraintExplorerEntryResponse(BackendBaseModel):
    constraint_id: str
    source: ConstraintSource
    operation_id: str
    property_path: str
    expression: str
    section: str | None = None
    parameter: str | None = None
    constraint_kind: ConstraintKind
    source_type: str | None = None
    static_expression: str | None = None
    dynamic_expression: str | None = None
    combined_expression: str | None = None
    has_static: bool
    has_dynamic: bool
    agreement_status: AgreementStatus
    assertion_available: bool
    assertion_preview: str | None = None

    @classmethod
    def from_domain(
        cls, entry: ConstraintExplorerEntry
    ) -> "ConstraintExplorerEntryResponse":
        return cls(
            constraint_id=entry.constraint_id,
            source=entry.source,
            operation_id=entry.operation_id,
            property_path=entry.property_path,
            expression=entry.expression,
            section=entry.section,
            parameter=entry.parameter,
            constraint_kind=entry.constraint_kind,
            source_type=entry.source_type,
            static_expression=entry.static_expression,
            dynamic_expression=entry.dynamic_expression,
            combined_expression=entry.combined_expression,
            has_static=entry.has_static,
            has_dynamic=entry.has_dynamic,
            agreement_status=entry.agreement_status,
            assertion_available=entry.assertion_available,
            assertion_preview=entry.assertion_preview,
        )


class ConstraintExplorerDetailResponse(ConstraintExplorerEntryResponse):
    assertion: str | None = None

    @classmethod
    def from_domain(
        cls, entry: ConstraintExplorerDetail
    ) -> "ConstraintExplorerDetailResponse":
        return cls(
            **ConstraintExplorerEntryResponse.from_domain(entry).model_dump(),
            assertion=entry.assertion,
        )


class ConstraintExplorerPageResponse(BackendBaseModel):
    run_name: str
    items: list[ConstraintExplorerEntryResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]
    metadata: ConstraintQueryMetadataResponse

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: ConstraintExplorerPage,
    ) -> "ConstraintExplorerPageResponse":
        return cls(
            run_name=run_name,
            items=[
                ConstraintExplorerEntryResponse.from_domain(item)
                for item in page.items
            ],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
            metadata=ConstraintQueryMetadataResponse.from_domain(page.metadata),
        )


class ConstraintFacetBucketResponse(BackendBaseModel):
    key: str
    count: int = Field(ge=0)

    @classmethod
    def from_domain(
        cls, bucket: ConstraintFacetBucket
    ) -> "ConstraintFacetBucketResponse":
        return cls(key=bucket.key, count=bucket.count)


class ConstraintFacetsResponse(BackendBaseModel):
    source: list[ConstraintFacetBucketResponse]
    operation_id: list[ConstraintFacetBucketResponse]
    section: list[ConstraintFacetBucketResponse]
    constraint_kind: list[ConstraintFacetBucketResponse]
    source_type: list[ConstraintFacetBucketResponse]
    agreement_status: list[ConstraintFacetBucketResponse]
    assertion_available: list[ConstraintFacetBucketResponse]
    metadata: ConstraintQueryMetadataResponse

    @classmethod
    def from_domain(cls, facets: ConstraintFacets) -> "ConstraintFacetsResponse":
        return cls(
            source=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.source
            ],
            operation_id=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.operation_id
            ],
            section=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.section
            ],
            constraint_kind=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.constraint_kind
            ],
            source_type=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.source_type
            ],
            agreement_status=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.agreement_status
            ],
            assertion_available=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.assertion_available
            ],
            metadata=ConstraintQueryMetadataResponse.from_domain(facets.metadata),
        )


class CombinationEntryResponse(BackendBaseModel):
    combination_id: str
    operation_id: str
    property_path: str
    status: str
    verdict: str | None = None
    resolved: bool
    static_constraint: str | None = None
    dynamic_constraint: str | None = None
    final_constraint: str | None = None
    reason_preview: str | None = None
    has_counter_example: bool
    has_runtime_evaluation: bool
    validation_case_count: int = Field(ge=0)
    source_artifact: str

    @classmethod
    def from_domain(cls, entry: CombinationEntry) -> "CombinationEntryResponse":
        return cls(
            combination_id=entry.combination_id,
            operation_id=entry.operation_id,
            property_path=entry.property_path,
            status=entry.status,
            verdict=entry.verdict,
            resolved=entry.resolved,
            static_constraint=entry.static_constraint,
            dynamic_constraint=entry.dynamic_constraint,
            final_constraint=entry.final_constraint,
            reason_preview=entry.reason_preview,
            has_counter_example=entry.has_counter_example,
            has_runtime_evaluation=entry.has_runtime_evaluation,
            validation_case_count=entry.validation_case_count,
            source_artifact=entry.source_artifact,
        )


class CombinationDetailResponse(CombinationEntryResponse):
    reason: str | None = None
    counter_example: JsonValue | None = None
    runtime_evaluation: JsonValue | None = None
    validation_cases: list[JsonValue]
    raw_record_sanitized: dict[str, JsonValue]

    @classmethod
    def from_domain(cls, entry: CombinationDetail) -> "CombinationDetailResponse":
        return cls(
            **CombinationEntryResponse.from_domain(entry).model_dump(),
            reason=entry.reason,
            counter_example=entry.counter_example,
            runtime_evaluation=entry.runtime_evaluation,
            validation_cases=entry.validation_cases,
            raw_record_sanitized=entry.raw_record_sanitized,
        )


class CombinationSummaryResponse(BackendBaseModel):
    run_name: str
    source_artifact: str
    endpoint_count: int = Field(ge=0)
    property_count: int = Field(ge=0)
    resolved_count: int = Field(ge=0)
    unresolved_count: int = Field(ge=0)
    malformed_count: int = Field(ge=0)
    status_counts: dict[str, int]
    verdict_counts: dict[str, int]
    warnings: list[str]

    @classmethod
    def from_domain(cls, summary: CombinationSummary) -> "CombinationSummaryResponse":
        return cls(
            run_name=summary.run_name,
            source_artifact=summary.source_artifact,
            endpoint_count=summary.endpoint_count,
            property_count=summary.property_count,
            resolved_count=summary.resolved_count,
            unresolved_count=summary.unresolved_count,
            malformed_count=summary.malformed_count,
            status_counts=summary.status_counts,
            verdict_counts=summary.verdict_counts,
            warnings=summary.warnings,
        )


class CombinationEntryPageResponse(BackendBaseModel):
    run_name: str
    items: list[CombinationEntryResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]
    malformed_count: int = Field(ge=0)
    warnings: list[str]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: CombinationEntryPage,
    ) -> "CombinationEntryPageResponse":
        return cls(
            run_name=run_name,
            items=[CombinationEntryResponse.from_domain(item) for item in page.items],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
            malformed_count=page.malformed_count,
            warnings=page.warnings,
        )


class CombinationFacetsResponse(BackendBaseModel):
    status: list[ConstraintFacetBucketResponse]
    verdict: list[ConstraintFacetBucketResponse]
    resolved: list[ConstraintFacetBucketResponse]
    operation_id: list[ConstraintFacetBucketResponse]
    has_counter_example: list[ConstraintFacetBucketResponse]
    has_runtime_evaluation: list[ConstraintFacetBucketResponse]
    has_validation_cases: list[ConstraintFacetBucketResponse]
    malformed_count: int = Field(ge=0)
    warnings: list[str]

    @classmethod
    def from_domain(cls, facets: CombinationFacets) -> "CombinationFacetsResponse":
        return cls(
            status=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.status
            ],
            verdict=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.verdict
            ],
            resolved=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.resolved
            ],
            operation_id=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.operation_id
            ],
            has_counter_example=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_counter_example
            ],
            has_runtime_evaluation=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_runtime_evaluation
            ],
            has_validation_cases=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_validation_cases
            ],
            malformed_count=facets.malformed_count,
            warnings=facets.warnings,
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


class InvariantCorrelationEvidenceResponse(BackendBaseModel):
    evidence_type: str
    message: str
    property_path: str | None = None
    constraint_id: str | None = None

    @classmethod
    def from_domain(
        cls, evidence: InvariantCorrelationEvidence
    ) -> "InvariantCorrelationEvidenceResponse":
        return cls(
            evidence_type=evidence.evidence_type,
            message=evidence.message,
            property_path=evidence.property_path,
            constraint_id=evidence.constraint_id,
        )


class InvariantExplorerEntryResponse(BackendBaseModel):
    invariant_id: str
    operation_id: str | None = None
    pptname: str | None = None
    invariant: str | None = None
    invariant_type: str | None = None
    variables: str | None = None
    property_paths: list[str]
    primary_property_path: str | None = None
    invariant_kind: InvariantKind
    oracle_readiness: OracleReadiness
    assertion_available: bool
    assertion_preview: str | None = None
    postman_assertion: str | None = None
    related_constraint_ids: list[str]
    correlation_confidence: CorrelationConfidence
    correlation_evidence: list[InvariantCorrelationEvidenceResponse]

    @classmethod
    def from_domain(
        cls, invariant: InvariantExplorerEntry
    ) -> "InvariantExplorerEntryResponse":
        return cls(
            invariant_id=invariant.invariant_id,
            operation_id=invariant.operation_id,
            pptname=invariant.pptname,
            invariant=invariant.invariant,
            invariant_type=invariant.invariant_type,
            variables=invariant.variables,
            property_paths=invariant.property_paths,
            primary_property_path=invariant.primary_property_path,
            invariant_kind=invariant.invariant_kind,
            oracle_readiness=invariant.oracle_readiness,
            assertion_available=invariant.assertion_available,
            assertion_preview=invariant.assertion_preview,
            related_constraint_ids=invariant.related_constraint_ids,
            correlation_confidence=invariant.correlation_confidence,
            correlation_evidence=[
                InvariantCorrelationEvidenceResponse.from_domain(item)
                for item in invariant.correlation_evidence
            ],
        )


class InvariantExplorerDetailResponse(InvariantExplorerEntryResponse):
    postman_assertion: str | None = None

    @classmethod
    def from_domain(
        cls, invariant: InvariantExplorerDetail
    ) -> "InvariantExplorerDetailResponse":
        base = InvariantExplorerEntryResponse.from_domain(invariant).model_dump()
        base["postman_assertion"] = invariant.postman_assertion
        return cls(**base)


class InvariantExplorerPageResponse(BackendBaseModel):
    run_name: str
    items: list[InvariantExplorerEntryResponse]
    pagination: PaginationMetadata
    groups: list[GroupCountResponse]

    @classmethod
    def from_domain(
        cls,
        run_name: str,
        page: InvariantExplorerPage,
    ) -> "InvariantExplorerPageResponse":
        return cls(
            run_name=run_name,
            items=[
                InvariantExplorerEntryResponse.from_domain(item) for item in page.items
            ],
            pagination=PaginationMetadata.from_domain(page.pagination),
            groups=[GroupCountResponse.from_domain(group) for group in page.groups],
        )


class InvariantExplorerFacetsResponse(BackendBaseModel):
    operation_id: list[ConstraintFacetBucketResponse]
    invariant_kind: list[ConstraintFacetBucketResponse]
    invariant_type: list[ConstraintFacetBucketResponse]
    oracle_readiness: list[ConstraintFacetBucketResponse]
    assertion_available: list[ConstraintFacetBucketResponse]
    correlation_confidence: list[ConstraintFacetBucketResponse]
    primary_property_path: list[ConstraintFacetBucketResponse]

    @classmethod
    def from_domain(
        cls, facets: InvariantExplorerFacets
    ) -> "InvariantExplorerFacetsResponse":
        return cls(
            operation_id=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.operation_id
            ],
            invariant_kind=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.invariant_kind
            ],
            invariant_type=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.invariant_type
            ],
            oracle_readiness=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.oracle_readiness
            ],
            assertion_available=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.assertion_available
            ],
            correlation_confidence=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.correlation_confidence
            ],
            primary_property_path=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.primary_property_path
            ],
        )


class InvariantGroupResponse(BackendBaseModel):
    operation_id: str
    invariants: list[JsonValue]

    @classmethod
    def from_domain(cls, group: InvariantGroup) -> "InvariantGroupResponse":
        return cls(operation_id=group.operation_id, invariants=group.invariants)


class DynamicConstraintsResponse(BackendBaseModel):
    run_name: str
    constraints: list[ConstraintEntryResponse] = Field(
        description="Mapped dynamic constraints derived from parsed and classified Daikon invariants."
    )
    groups: list[InvariantGroupResponse] = Field(
        description="Grouped raw invariant records from the dynamic mining artifact."
    )
    invariants: list[InvariantRecordResponse] = Field(
        description="Raw Daikon invariant rows used as provenance for mapped dynamic constraints."
    )
    constraint_count: int = Field(
        ge=0,
        description="Count of mapped dynamic constraints derived from raw Daikon invariants.",
    )
    invariant_count: int = Field(
        ge=0,
        description="Count of raw Daikon invariant rows included as dynamic constraint provenance.",
    )

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
