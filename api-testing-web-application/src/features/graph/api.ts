import {
  useGetDependencyGraphApiV1RunsRunNameGraphGet,
  useGetGraphEdgeApiV1RunsRunNameGraphEdgesEdgeIdGet,
  useGetGraphFacetsApiV1RunsRunNameGraphFacetsGet,
  useGetGraphSequenceApiV1RunsRunNameGraphSequencesSequenceIdGet,
  useListGraphEdgesApiV1RunsRunNameGraphEdgesGet,
  useListGraphNodesApiV1RunsRunNameGraphNodesGet,
  useListGraphSequencesApiV1RunsRunNameGraphSequencesGet,
} from '../../shared/api/generated/graph/graph'
import {
  useGetOperationApiV1RunsRunNameOperationGet,
  useListOperationsApiV1RunsRunNameOperationsGet,
} from '../../shared/api/generated/operations/operations'
import type {
  GetGraphFacetsApiV1RunsRunNameGraphFacetsGetParams,
  ListGraphEdgesApiV1RunsRunNameGraphEdgesGetParams,
  ListGraphNodesApiV1RunsRunNameGraphNodesGetParams,
  ListGraphSequencesApiV1RunsRunNameGraphSequencesGetParams,
  SortOrder,
} from '../../shared/api/generated/model'

export type GraphExplorerFilters = {
  edgeStatus?: string
  evidenceSource?: string
  fromNode?: string
  fromOperationId?: string
  groupBy?: string
  limit?: number
  nodeKind?: string
  offset?: number
  operationId?: string
  q?: string
  sequenceType?: string
  sortBy?: string
  sortOrder?: SortOrder
  targetOperationId?: string
  toNode?: string
  toOperationId?: string
}

export function toGraphEdgeParams(filters: GraphExplorerFilters): ListGraphEdgesApiV1RunsRunNameGraphEdgesGetParams {
  return {
    edge_status: filters.edgeStatus,
    evidence_source: filters.evidenceSource,
    from_node: filters.fromNode,
    from_operation_id: filters.fromOperationId,
    group_by: filters.groupBy,
    limit: filters.limit,
    offset: filters.offset,
    q: filters.q,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
    to_node: filters.toNode,
    to_operation_id: filters.toOperationId,
  }
}

export function toGraphFacetParams(filters: GraphExplorerFilters): GetGraphFacetsApiV1RunsRunNameGraphFacetsGetParams {
  return {
    edge_status: filters.edgeStatus,
    evidence_source: filters.evidenceSource,
    from_operation_id: filters.fromOperationId,
    node_kind: filters.nodeKind,
    q: filters.q,
    sequence_type: filters.sequenceType,
    to_operation_id: filters.toOperationId,
  }
}

export function toGraphNodeParams(filters: GraphExplorerFilters): ListGraphNodesApiV1RunsRunNameGraphNodesGetParams {
  return {
    group_by: filters.groupBy,
    limit: filters.limit,
    node_kind: filters.nodeKind,
    offset: filters.offset,
    operation_id: filters.operationId,
    q: filters.q,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
  }
}

export function toGraphSequenceParams(
  filters: GraphExplorerFilters,
): ListGraphSequencesApiV1RunsRunNameGraphSequencesGetParams {
  return {
    group_by: filters.groupBy,
    limit: filters.limit,
    offset: filters.offset,
    operation_id: filters.operationId,
    q: filters.q,
    sequence_type: filters.sequenceType,
    sort_by: filters.sortBy,
    sort_order: filters.sortOrder,
    target_operation_id: filters.targetOperationId,
  }
}

export const useDependencyGraph = useGetDependencyGraphApiV1RunsRunNameGraphGet
export const useGraphEdges = useListGraphEdgesApiV1RunsRunNameGraphEdgesGet
export const useGraphEdgeDetail = useGetGraphEdgeApiV1RunsRunNameGraphEdgesEdgeIdGet
export const useGraphFacets = useGetGraphFacetsApiV1RunsRunNameGraphFacetsGet
export const useGraphNodes = useListGraphNodesApiV1RunsRunNameGraphNodesGet
export const useGraphSequences = useListGraphSequencesApiV1RunsRunNameGraphSequencesGet
export const useGraphSequenceDetail = useGetGraphSequenceApiV1RunsRunNameGraphSequencesSequenceIdGet
export const useOperations = useListOperationsApiV1RunsRunNameOperationsGet
export const useOperationDetail = useGetOperationApiV1RunsRunNameOperationGet
