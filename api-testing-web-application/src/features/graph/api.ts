import {
  useGetDependencyGraphApiV1RunsRunNameGraphGet,
  useListGraphEdgesApiV1RunsRunNameGraphEdgesGet,
} from '../../shared/api/generated/graph/graph'
import {
  useGetOperationApiV1RunsRunNameOperationGet,
  useListOperationsApiV1RunsRunNameOperationsGet,
} from '../../shared/api/generated/operations/operations'

export const useDependencyGraph = useGetDependencyGraphApiV1RunsRunNameGraphGet
export const useGraphEdges = useListGraphEdgesApiV1RunsRunNameGraphEdgesGet
export const useOperations = useListOperationsApiV1RunsRunNameOperationsGet
export const useOperationDetail = useGetOperationApiV1RunsRunNameOperationGet
