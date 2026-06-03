from __future__ import annotations

from pydantic import Field, JsonValue, model_validator

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
from api_testing.backend.domain.review_models import (
    CombinationReviewDetail,
    CombinationReviewEvent,
    CounterExampleCase,
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
    combination_id: str | None = None
    review_state: str | None = None
    decision_source: str | None = None
    has_manual_decision: bool = False
    manual_decision: str | None = None
    manual_final_constraint: str | None = None

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
            combination_id=entry.combination_id,
            review_state=entry.review_state,
            decision_source=entry.decision_source,
            has_manual_decision=entry.has_manual_decision,
            manual_decision=entry.manual_decision,
            manual_final_constraint=entry.manual_final_constraint,
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
    review_state: list[ConstraintFacetBucketResponse]
    decision_source: list[ConstraintFacetBucketResponse]
    has_manual_decision: list[ConstraintFacetBucketResponse]
    manual_decision: list[ConstraintFacetBucketResponse]
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
            review_state=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.review_state
            ],
            decision_source=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.decision_source
            ],
            has_manual_decision=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_manual_decision
            ],
            manual_decision=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.manual_decision
            ],
            metadata=ConstraintQueryMetadataResponse.from_domain(facets.metadata),
        )


class CombinationEntryResponse(BackendBaseModel):
    combination_id: str
    operation_id: str
    property_path: str
    status: str
    relation: str | None = None
    runtime_verdict: str | None = None
    resolved: bool
    static_constraint: str | None = None
    dynamic_constraint: str | None = None
    final_constraint: str | None = None
    reason_preview: str | None = None
    has_counter_example: bool
    has_runtime_evaluation: bool
    validation_case_count: int = Field(ge=0)
    source_artifact: str
    review_state: str = "PENDING_REVIEW"
    decision_source: str | None = None
    has_manual_decision: bool = False

    @classmethod
    def from_domain(cls, entry: CombinationEntry) -> "CombinationEntryResponse":
        return cls(
            combination_id=entry.combination_id,
            operation_id=entry.operation_id,
            property_path=entry.property_path,
            status=entry.status,
            relation=entry.relation,
            runtime_verdict=entry.runtime_verdict,
            resolved=entry.resolved,
            static_constraint=entry.static_constraint,
            dynamic_constraint=entry.dynamic_constraint,
            final_constraint=entry.final_constraint,
            reason_preview=entry.reason_preview,
            has_counter_example=entry.has_counter_example,
            has_runtime_evaluation=entry.has_runtime_evaluation,
            validation_case_count=entry.validation_case_count,
            source_artifact=entry.source_artifact,
            review_state=entry.review_state,
            decision_source=entry.decision_source,
            has_manual_decision=entry.has_manual_decision,
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
    relation_counts: dict[str, int]
    runtime_verdict_counts: dict[str, int]
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
            relation_counts=summary.relation_counts,
            runtime_verdict_counts=summary.runtime_verdict_counts,
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
    relation: list[ConstraintFacetBucketResponse]
    runtime_verdict: list[ConstraintFacetBucketResponse]
    resolved: list[ConstraintFacetBucketResponse]
    operation_id: list[ConstraintFacetBucketResponse]
    has_counter_example: list[ConstraintFacetBucketResponse]
    has_runtime_evaluation: list[ConstraintFacetBucketResponse]
    has_validation_cases: list[ConstraintFacetBucketResponse]
    review_state: list[ConstraintFacetBucketResponse]
    decision_source: list[ConstraintFacetBucketResponse]
    has_manual_decision: list[ConstraintFacetBucketResponse]
    malformed_count: int = Field(ge=0)
    warnings: list[str]

    @classmethod
    def from_domain(cls, facets: CombinationFacets) -> "CombinationFacetsResponse":
        return cls(
            status=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.status
            ],
            relation=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.relation
            ],
            runtime_verdict=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.runtime_verdict
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
            review_state=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.review_state
            ],
            decision_source=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.decision_source
            ],
            has_manual_decision=[
                ConstraintFacetBucketResponse.from_domain(bucket)
                for bucket in facets.has_manual_decision
            ],
            malformed_count=facets.malformed_count,
            warnings=facets.warnings,
        )


class CounterExampleCaseResponse(BackendBaseModel):
    case_id: str
    case_state: str
    request: JsonValue
    request_display: JsonValue | None = None
    source: str
    rationale: str | None = None
    generation_id: str | None = None
    target_truth_vector: JsonValue | None = None
    risk: str | None = None
    expected_observation: str | None = None
    validation_error: JsonValue | None = None
    planner_version: str | None = None
    source_metadata: JsonValue | None = None
    runtime_verdict: str | None = None
    runtime_result: JsonValue | None = None

    @classmethod
    def from_domain(cls, case: CounterExampleCase) -> "CounterExampleCaseResponse":
        return cls(
            case_id=case.case_id,
            case_state=case.case_state,
            request=case.request,
            request_display=case.request_display,
            source=case.source,
            rationale=case.rationale,
            generation_id=case.generation_id,
            target_truth_vector=case.target_truth_vector,
            risk=case.risk,
            expected_observation=case.expected_observation,
            validation_error=case.validation_error,
            planner_version=case.planner_version,
            source_metadata=case.source_metadata,
            runtime_verdict=case.runtime_verdict,
            runtime_result=case.runtime_result,
        )


class CombinationReviewEventResponse(BackendBaseModel):
    sequence: int = Field(ge=1)
    event_type: str
    metadata: JsonValue

    @classmethod
    def from_domain(
        cls, event: CombinationReviewEvent
    ) -> "CombinationReviewEventResponse":
        return cls(
            sequence=event.sequence,
            event_type=event.event_type,
            metadata=event.metadata,
        )


class CombinationReviewResponse(BackendBaseModel):
    run_name: str
    combination_id: str
    review_key: str
    review_state: str
    decision_source: str | None = None
    manual_decision: str | None = None
    rationale: str | None = None
    custom_final_constraint: str | None = None
    runtime_recommendation: str | None = None
    has_manual_decision: bool
    target_base_url_suggestions: list[str] = []
    cases: list[CounterExampleCaseResponse]
    events: list[CombinationReviewEventResponse]

    @classmethod
    def from_domain(
        cls, detail: CombinationReviewDetail
    ) -> "CombinationReviewResponse":
        review = detail.review
        return cls(
            run_name=review.run_name,
            combination_id=review.combination_id,
            review_key=review.review_key,
            review_state=review.review_state,
            decision_source=review.decision_source,
            manual_decision=review.manual_decision,
            rationale=review.rationale,
            custom_final_constraint=review.custom_final_constraint,
            runtime_recommendation=review.runtime_recommendation,
            has_manual_decision=review.manual_decision is not None,
            target_base_url_suggestions=detail.target_base_url_suggestions,
            cases=[CounterExampleCaseResponse.from_domain(case) for case in detail.cases],
            events=[
                CombinationReviewEventResponse.from_domain(event)
                for event in detail.events
            ],
        )


class CounterExampleGenerateResponse(CombinationReviewResponse):
    pass


class CounterExampleGenerateRequest(BackendBaseModel):
    live_llm: bool = False
    idempotency_key: str = Field(min_length=1)
    max_cases: int | None = Field(default=None, ge=1, le=10)


class CounterExampleCaseUpdateRequest(BackendBaseModel):
    case_state: str
    rationale: str | None = None
    request: JsonValue | None = None


class CounterExampleRunRequest(BackendBaseModel):
    live_api: bool
    base_url: str | None = None
    request_budget: int = Field(gt=0)
    timeout_seconds: int = Field(gt=0)
    unsafe_method_confirmed: bool = False
    idempotency_key: str = Field(min_length=1)


class CombinationReviewFinalizeRequest(BackendBaseModel):
    manual_decision: str
    idempotency_key: str = Field(min_length=1)
    rationale: str | None = None
    custom_final_constraint: str | None = None

    @model_validator(mode="after")
    def validate_decision(self) -> "CombinationReviewFinalizeRequest":
        allowed = {
            "ACCEPT_STATIC",
            "ACCEPT_DYNAMIC",
            "CUSTOM_FINAL",
            "NO_FINAL",
            "NEEDS_BUSINESS_REVIEW",
            "REJECT_RELATION",
        }
        if self.manual_decision not in allowed:
            raise ValueError(f"Unsupported manual_decision: {self.manual_decision}")
        if not self.rationale or not self.rationale.strip():
            raise ValueError("rationale is required")
        if self.manual_decision == "CUSTOM_FINAL" and (
            not self.custom_final_constraint
            or not self.custom_final_constraint.strip()
        ):
            raise ValueError("custom_final_constraint is required for CUSTOM_FINAL")
        return self


class CombinationReviewReopenRequest(BackendBaseModel):
    rationale: str


class BatchCounterExampleGenerateRequest(BackendBaseModel):
    combination_ids: list[str] = Field(min_length=1)
    live_llm: bool = False
    idempotency_key: str = Field(min_length=1)
    max_items: int | None = Field(default=None, ge=1, le=100)
    max_cases_per_item: int | None = Field(default=None, ge=1, le=10)


class BatchCounterExampleGenerateItemResponse(BackendBaseModel):
    combination_id: str
    status: str
    case_count: int = Field(ge=0)
    new_case_count: int = Field(default=0, ge=0)
    total_case_count: int = Field(default=0, ge=0)
    message: str | None = None


class BatchCounterExampleGenerateResponse(BackendBaseModel):
    results: list[BatchCounterExampleGenerateItemResponse]


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
