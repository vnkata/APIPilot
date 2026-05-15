import {
  useGetOperationExplorerEntryApiV1RunsRunNameOperationsEntriesOperationKeyGet,
  useGetOperationExplorerFacetsApiV1RunsRunNameOperationsFacetsGet,
  useListOperationExplorerEntriesApiV1RunsRunNameOperationsEntriesGet,
} from '../../shared/api/generated/operations/operations'
import type {
  GetOperationExplorerFacetsApiV1RunsRunNameOperationsFacetsGetParams,
  ListOperationExplorerEntriesApiV1RunsRunNameOperationsEntriesGetParams,
  SortOrder,
} from '../../shared/api/generated/model'

export type OperationExplorerFilters = {
  groupBy?: string
  hasConstraints?: boolean
  hasFailures?: boolean
  hasGraphEdges?: boolean
  hasInvariants?: boolean
  hasRequestBody?: boolean
  httpMethod?: string
  limit?: number
  offset?: number
  operationId?: string
  operationKey?: string
  q?: string
  responseStatus?: string
  sortBy?: string
  sortOrder?: SortOrder
}

export function toOperationExplorerParams(
  filters: OperationExplorerFilters,
): ListOperationExplorerEntriesApiV1RunsRunNameOperationsEntriesGetParams {
  return {
    group_by: filters.groupBy,
    has_constraints: filters.hasConstraints,
    has_failures: filters.hasFailures,
    has_graph_edges: filters.hasGraphEdges,
    has_invariants: filters.hasInvariants,
    has_request_body: filters.hasRequestBody,
    http_method: filters.httpMethod,
    limit: filters.limit,
    offset: filters.offset,
    operation_id: filters.operationId,
    operation_key: filters.operationKey,
    q: filters.q,
    response_status: filters.responseStatus,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
  }
}

export function toOperationFacetParams(
  filters: OperationExplorerFilters,
): GetOperationExplorerFacetsApiV1RunsRunNameOperationsFacetsGetParams {
  return {
    has_constraints: filters.hasConstraints,
    has_failures: filters.hasFailures,
    has_graph_edges: filters.hasGraphEdges,
    has_invariants: filters.hasInvariants,
    has_request_body: filters.hasRequestBody,
    http_method: filters.httpMethod,
    operation_id: filters.operationId,
    q: filters.q,
    response_status: filters.responseStatus,
  }
}

export const useOperationExplorerEntries = useListOperationExplorerEntriesApiV1RunsRunNameOperationsEntriesGet
export const useOperationExplorerDetail = useGetOperationExplorerEntryApiV1RunsRunNameOperationsEntriesOperationKeyGet
export const useOperationExplorerFacets = useGetOperationExplorerFacetsApiV1RunsRunNameOperationsFacetsGet
