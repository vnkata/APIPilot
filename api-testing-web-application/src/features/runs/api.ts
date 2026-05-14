import {
  useGetRunApiV1RunsRunNameGet,
  useGetRunSummaryApiV1RunsRunNameSummaryGet,
  useListRunsApiV1RunsGet,
} from '../../shared/api/generated/runs/runs'
import { useListArtifactsApiV1RunsRunNameArtifactsGet } from '../../shared/api/generated/artifacts/artifacts'
import { useListHarSessionsApiV1RunsRunNameHistorySessionsGet } from '../../shared/api/generated/history/history'
import { useListOperationsApiV1RunsRunNameOperationsGet } from '../../shared/api/generated/operations/operations'

export const useRuns = useListRunsApiV1RunsGet
export const useRunMetadata = useGetRunApiV1RunsRunNameGet
export const useRunSummary = useGetRunSummaryApiV1RunsRunNameSummaryGet
export const useRunOperations = useListOperationsApiV1RunsRunNameOperationsGet
export const useRunArtifacts = useListArtifactsApiV1RunsRunNameArtifactsGet
export const useRunHarSessions = useListHarSessionsApiV1RunsRunNameHistorySessionsGet
