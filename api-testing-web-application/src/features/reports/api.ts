import {
  useGetReportsApiV1RunsRunNameReportsGet,
  useListReportEntriesApiV1RunsRunNameReportsEntriesGet,
} from '../../shared/api/generated/reports/reports'

export const useReports = useGetReportsApiV1RunsRunNameReportsGet
export const useReportEntries = useListReportEntriesApiV1RunsRunNameReportsEntriesGet
