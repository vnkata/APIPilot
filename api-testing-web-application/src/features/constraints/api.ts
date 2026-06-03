import {
  useBatchGenerateCounterExamplesApiV1RunsRunNameConstraintsCombinationCounterExamplesBatchGeneratePost,
  useFinalizeCombinationReviewApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdReviewFinalizePost,
  useGetCombinationEntryApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdGet,
  useGetCombinationFacetsApiV1RunsRunNameConstraintsCombinationFacetsGet,
  useGetCombinationReviewApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdReviewGet,
  useGetCombinationSummaryApiV1RunsRunNameConstraintsCombinationSummaryGet,
  useGetConstraintExplorerEntryApiV1RunsRunNameConstraintsEntriesConstraintIdGet,
  useGetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGet,
  useGetDynamicConstraintsApiV1RunsRunNameConstraintsDynamicGet,
  useGetInvariantExplorerEntryApiV1RunsRunNameConstraintsInvariantsInvariantIdGet,
  useGetInvariantExplorerFacetsApiV1RunsRunNameConstraintsInvariantsFacetsGet,
  useGetStaticConstraintsApiV1RunsRunNameConstraintsStaticGet,
  useListCombinationEntriesApiV1RunsRunNameConstraintsCombinationEntriesGet,
  useListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGet,
  useListDynamicConstraintEntriesApiV1RunsRunNameConstraintsDynamicEntriesGet,
  useListDynamicInvariantsApiV1RunsRunNameConstraintsDynamicInvariantsGet,
  useListInvariantExplorerEntriesApiV1RunsRunNameConstraintsInvariantsGet,
  useListStaticConstraintEntriesApiV1RunsRunNameConstraintsStaticEntriesGet,
  useGenerateCounterExamplesApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdCounterExamplesGeneratePost,
  useReopenCombinationReviewApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdReviewReopenPost,
  useRunCounterExamplesApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdCounterExamplesRunPost,
  useUpdateCounterExampleCaseApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdCounterExamplesCaseIdPut,
} from '../../shared/api/generated/constraints/constraints'
import type {
  GetCombinationFacetsApiV1RunsRunNameConstraintsCombinationFacetsGetParams,
  GetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGetParams,
  GetInvariantExplorerFacetsApiV1RunsRunNameConstraintsInvariantsFacetsGetParams,
  ListCombinationEntriesApiV1RunsRunNameConstraintsCombinationEntriesGetParams,
  ListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGetParams,
  ListInvariantExplorerEntriesApiV1RunsRunNameConstraintsInvariantsGetParams,
  SortOrder,
} from '../../shared/api/generated/model'

export type ConstraintExplorerFilters = {
  agreementStatus?: string
  assertionAvailable?: boolean
  constraintKind?: string
  correlationConfidence?: string
  decisionSource?: string
  groupBy?: string
  hasCounterExample?: boolean
  hasManualDecision?: boolean
  hasRuntimeEvaluation?: boolean
  hasValidationCases?: boolean
  invariantKind?: string
  invariantType?: string
  limit?: number
  manualDecision?: string
  offset?: number
  operationId?: string
  oracleReadiness?: string
  propertyPath?: string
  propertyPrefix?: string
  q?: string
  relation?: string
  reviewState?: string
  resolved?: boolean
  section?: string
  sortBy?: string
  sortOrder?: SortOrder
  source?: string
  sourceType?: string
  status?: string
  runtimeVerdict?: string
}

export function toConstraintExplorerParams(
  filters: ConstraintExplorerFilters,
): ListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGetParams {
  return {
    agreement_status: filters.agreementStatus,
    assertion_available: filters.assertionAvailable,
    constraint_kind: filters.constraintKind,
    decision_source: filters.decisionSource,
    group_by: filters.groupBy,
    has_manual_decision: filters.hasManualDecision,
    limit: filters.limit,
    manual_decision: filters.manualDecision,
    offset: filters.offset,
    operation_id: filters.operationId,
    property_path: filters.propertyPath,
    property_prefix: filters.propertyPrefix,
    q: filters.q,
    section: filters.section,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
    source: filters.source,
    source_type: filters.sourceType,
    review_state: filters.reviewState,
  }
}

export function toConstraintFacetParams(
  filters: ConstraintExplorerFilters,
): GetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGetParams {
  return {
    agreement_status: filters.agreementStatus,
    assertion_available: filters.assertionAvailable,
    constraint_kind: filters.constraintKind,
    decision_source: filters.decisionSource,
    has_manual_decision: filters.hasManualDecision,
    manual_decision: filters.manualDecision,
    operation_id: filters.operationId,
    property_path: filters.propertyPath,
    property_prefix: filters.propertyPrefix,
    q: filters.q,
    section: filters.section,
    source: filters.source,
    source_type: filters.sourceType,
    review_state: filters.reviewState,
  }
}

export function toInvariantExplorerParams(
  filters: ConstraintExplorerFilters,
): ListInvariantExplorerEntriesApiV1RunsRunNameConstraintsInvariantsGetParams {
  return {
    assertion_available: filters.assertionAvailable,
    correlation_confidence: filters.correlationConfidence,
    group_by: filters.groupBy,
    invariant_kind: filters.invariantKind,
    invariant_type: filters.invariantType,
    limit: filters.limit,
    offset: filters.offset,
    operation_id: filters.operationId,
    oracle_readiness: filters.oracleReadiness,
    property_path: filters.propertyPath,
    property_prefix: filters.propertyPrefix,
    q: filters.q,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
  }
}

export function toInvariantFacetParams(
  filters: ConstraintExplorerFilters,
): GetInvariantExplorerFacetsApiV1RunsRunNameConstraintsInvariantsFacetsGetParams {
  return {
    assertion_available: filters.assertionAvailable,
    correlation_confidence: filters.correlationConfidence,
    invariant_kind: filters.invariantKind,
    invariant_type: filters.invariantType,
    operation_id: filters.operationId,
    oracle_readiness: filters.oracleReadiness,
    property_path: filters.propertyPath,
    property_prefix: filters.propertyPrefix,
    q: filters.q,
  }
}

export function toCombinationParams(
  filters: ConstraintExplorerFilters,
): ListCombinationEntriesApiV1RunsRunNameConstraintsCombinationEntriesGetParams {
  return {
    group_by: filters.groupBy,
    has_counter_example: filters.hasCounterExample,
    has_runtime_evaluation: filters.hasRuntimeEvaluation,
    has_validation_cases: filters.hasValidationCases,
    limit: filters.limit,
    offset: filters.offset,
    operation_id: filters.operationId,
    property_path: filters.propertyPath,
    property_prefix: filters.propertyPrefix,
    q: filters.q,
    resolved: filters.resolved,
    relation: filters.relation,
    review_state: filters.reviewState,
    runtime_verdict: filters.runtimeVerdict,
    decision_source: filters.decisionSource,
    has_manual_decision: filters.hasManualDecision,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
    status: filters.status,
  }
}

export function toCombinationFacetParams(
  filters: ConstraintExplorerFilters,
): GetCombinationFacetsApiV1RunsRunNameConstraintsCombinationFacetsGetParams {
  return {
    has_counter_example: filters.hasCounterExample,
    has_runtime_evaluation: filters.hasRuntimeEvaluation,
    has_validation_cases: filters.hasValidationCases,
    operation_id: filters.operationId,
    property_path: filters.propertyPath,
    property_prefix: filters.propertyPrefix,
    q: filters.q,
    resolved: filters.resolved,
    relation: filters.relation,
    review_state: filters.reviewState,
    runtime_verdict: filters.runtimeVerdict,
    decision_source: filters.decisionSource,
    has_manual_decision: filters.hasManualDecision,
    status: filters.status,
  }
}

export const useStaticConstraintsSummary = useGetStaticConstraintsApiV1RunsRunNameConstraintsStaticGet
export const useStaticConstraintEntries = useListStaticConstraintEntriesApiV1RunsRunNameConstraintsStaticEntriesGet
export const useDynamicConstraintsSummary = useGetDynamicConstraintsApiV1RunsRunNameConstraintsDynamicGet
export const useDynamicConstraintEntries = useListDynamicConstraintEntriesApiV1RunsRunNameConstraintsDynamicEntriesGet
export const useDynamicInvariants = useListDynamicInvariantsApiV1RunsRunNameConstraintsDynamicInvariantsGet
export const useCombinationEntries = useListCombinationEntriesApiV1RunsRunNameConstraintsCombinationEntriesGet
export const useCombinationDetail = useGetCombinationEntryApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdGet
export const useCombinationFacets = useGetCombinationFacetsApiV1RunsRunNameConstraintsCombinationFacetsGet
export const useCombinationReview = useGetCombinationReviewApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdReviewGet
export const useCombinationSummary = useGetCombinationSummaryApiV1RunsRunNameConstraintsCombinationSummaryGet
export const useBatchGenerateCounterExamples = useBatchGenerateCounterExamplesApiV1RunsRunNameConstraintsCombinationCounterExamplesBatchGeneratePost
export const useFinalizeCombinationReview = useFinalizeCombinationReviewApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdReviewFinalizePost
export const useGenerateCounterExamples = useGenerateCounterExamplesApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdCounterExamplesGeneratePost
export const useReopenCombinationReview = useReopenCombinationReviewApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdReviewReopenPost
export const useRunCounterExamples = useRunCounterExamplesApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdCounterExamplesRunPost
export const useUpdateCounterExampleCase = useUpdateCounterExampleCaseApiV1RunsRunNameConstraintsCombinationEntriesCombinationIdCounterExamplesCaseIdPut
export const useConstraintExplorerEntries = useListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGet
export const useConstraintExplorerDetail = useGetConstraintExplorerEntryApiV1RunsRunNameConstraintsEntriesConstraintIdGet
export const useConstraintExplorerFacets = useGetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGet
export const useInvariantExplorerEntries = useListInvariantExplorerEntriesApiV1RunsRunNameConstraintsInvariantsGet
export const useInvariantExplorerDetail = useGetInvariantExplorerEntryApiV1RunsRunNameConstraintsInvariantsInvariantIdGet
export const useInvariantExplorerFacets = useGetInvariantExplorerFacetsApiV1RunsRunNameConstraintsInvariantsFacetsGet
