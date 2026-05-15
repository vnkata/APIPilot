import {
  useGetConstraintExplorerEntryApiV1RunsRunNameConstraintsEntriesConstraintIdGet,
  useGetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGet,
  useGetDynamicConstraintsApiV1RunsRunNameConstraintsDynamicGet,
  useGetInvariantExplorerEntryApiV1RunsRunNameConstraintsInvariantsInvariantIdGet,
  useGetInvariantExplorerFacetsApiV1RunsRunNameConstraintsInvariantsFacetsGet,
  useGetStaticConstraintsApiV1RunsRunNameConstraintsStaticGet,
  useListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGet,
  useListDynamicConstraintEntriesApiV1RunsRunNameConstraintsDynamicEntriesGet,
  useListDynamicInvariantsApiV1RunsRunNameConstraintsDynamicInvariantsGet,
  useListInvariantExplorerEntriesApiV1RunsRunNameConstraintsInvariantsGet,
  useListStaticConstraintEntriesApiV1RunsRunNameConstraintsStaticEntriesGet,
} from '../../shared/api/generated/constraints/constraints'
import type {
  GetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGetParams,
  GetInvariantExplorerFacetsApiV1RunsRunNameConstraintsInvariantsFacetsGetParams,
  ListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGetParams,
  ListInvariantExplorerEntriesApiV1RunsRunNameConstraintsInvariantsGetParams,
  SortOrder,
} from '../../shared/api/generated/model'

export type ConstraintExplorerFilters = {
  agreementStatus?: string
  assertionAvailable?: boolean
  constraintKind?: string
  correlationConfidence?: string
  groupBy?: string
  invariantKind?: string
  invariantType?: string
  limit?: number
  offset?: number
  operationId?: string
  oracleReadiness?: string
  propertyPath?: string
  propertyPrefix?: string
  q?: string
  section?: string
  sortBy?: string
  sortOrder?: SortOrder
  source?: string
  sourceType?: string
}

export function toConstraintExplorerParams(
  filters: ConstraintExplorerFilters,
): ListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGetParams {
  return {
    agreement_status: filters.agreementStatus,
    assertion_available: filters.assertionAvailable,
    constraint_kind: filters.constraintKind,
    group_by: filters.groupBy,
    limit: filters.limit,
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
  }
}

export function toConstraintFacetParams(
  filters: ConstraintExplorerFilters,
): GetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGetParams {
  return {
    agreement_status: filters.agreementStatus,
    assertion_available: filters.assertionAvailable,
    constraint_kind: filters.constraintKind,
    operation_id: filters.operationId,
    property_path: filters.propertyPath,
    property_prefix: filters.propertyPrefix,
    q: filters.q,
    section: filters.section,
    source: filters.source,
    source_type: filters.sourceType,
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

export const useStaticConstraintsSummary = useGetStaticConstraintsApiV1RunsRunNameConstraintsStaticGet
export const useStaticConstraintEntries = useListStaticConstraintEntriesApiV1RunsRunNameConstraintsStaticEntriesGet
export const useDynamicConstraintsSummary = useGetDynamicConstraintsApiV1RunsRunNameConstraintsDynamicGet
export const useDynamicConstraintEntries = useListDynamicConstraintEntriesApiV1RunsRunNameConstraintsDynamicEntriesGet
export const useDynamicInvariants = useListDynamicInvariantsApiV1RunsRunNameConstraintsDynamicInvariantsGet
export const useConstraintExplorerEntries = useListConstraintExplorerEntriesApiV1RunsRunNameConstraintsEntriesGet
export const useConstraintExplorerDetail = useGetConstraintExplorerEntryApiV1RunsRunNameConstraintsEntriesConstraintIdGet
export const useConstraintExplorerFacets = useGetConstraintExplorerFacetsApiV1RunsRunNameConstraintsFacetsGet
export const useInvariantExplorerEntries = useListInvariantExplorerEntriesApiV1RunsRunNameConstraintsInvariantsGet
export const useInvariantExplorerDetail = useGetInvariantExplorerEntryApiV1RunsRunNameConstraintsInvariantsInvariantIdGet
export const useInvariantExplorerFacets = useGetInvariantExplorerFacetsApiV1RunsRunNameConstraintsInvariantsFacetsGet
