import {
  useListHarEntriesApiV1RunsRunNameHistorySessionsSessionIdEntriesGet,
  useListHarSessionsApiV1RunsRunNameHistorySessionsGet,
} from '../../shared/api/generated/history/history'

export const useHarSessions = useListHarSessionsApiV1RunsRunNameHistorySessionsGet
export const useHarEntries = useListHarEntriesApiV1RunsRunNameHistorySessionsSessionIdEntriesGet
