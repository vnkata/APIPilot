import { useMemo, useState } from 'react'
import { Button, Card, CardContent, Grid, MenuItem, Stack, TextField, Typography } from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'

import type { StatusReportEntryResponse } from '../../shared/api/generated/model'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { MetricCard } from '../../shared/ui/MetricCard'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { useReportEntries, useReports } from './api'
import { StatusBarChart } from './StatusBarChart'

export type ReportsPageSearch = {
  groupBy?: string
  limit: number
  offset: number
  operationId?: string
  q?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  statusCode?: string
}

type ReportsPageProps = {
  runName: string
  search: ReportsPageSearch
}

type ReportRow = StatusReportEntryResponse & {
  id: string
}

function statusChartData(statusCounts: Record<string, number> | undefined) {
  return Object.entries(statusCounts ?? {}).map(([status, count]) => ({ count, status }))
}

export function ReportsPage({ runName, search }: ReportsPageProps) {
  const [exportOpen, setExportOpen] = useState(false)
  const gridState = useUrlBackedGridState(search)
  const reportsQuery = useReports(runName)
  const entriesQuery = useReportEntries(runName, {
    group_by: search.groupBy,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    q: search.q,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
    status_code: search.statusCode,
  })
  const rows: ReportRow[] = (entriesQuery.data?.items ?? []).map((item) => ({
    ...item,
    id: `${item.operation_id}:${item.status_code}`,
  }))
  const reportColumns = useMemo<GridColDef<ReportRow>[]>(
    () => [
      {
        field: 'operation_id',
        flex: 1.2,
        headerName: 'Operation',
        minWidth: 180,
        renderCell: (params) => (
          <Button
            onClick={() => replaceSearchParams({ operationId: params.row.operation_id })}
            size="small"
          >
            {params.row.operation_id}
          </Button>
        ),
      },
      { field: 'status_code', flex: 0.6, headerName: 'Status', minWidth: 120 },
      { field: 'count', flex: 0.5, headerName: 'Count', minWidth: 100, type: 'number' },
    ],
    [],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Button onClick={() => setExportOpen(true)} variant="outlined">
            Export snapshot
          </Button>
        }
        eyebrow="Report analyzer"
        title="Reports"
        subtitle="Aggregate APIPilot status report entries and inspect operation/status distribution."
      />

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <MetricCard
            label="Report entries"
            value={reportsQuery.data?.entries.length ?? 0}
            caption="Loaded from /reports"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <MetricCard
            label="Paginated rows"
            value={entriesQuery.data?.pagination.total ?? 0}
            caption="Loaded from /reports/entries"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <MetricCard
            label="Distinct statuses"
            value={Object.keys(reportsQuery.data?.status_counts ?? {}).length}
          />
        </Grid>
      </Grid>

      <Card variant="outlined">
        <CardContent>
          <Typography component="h2" sx={{ mb: 2 }} variant="h3">
            Status distribution
          </Typography>
          <QueryState
            empty={(reportsQuery.data?.entries.length ?? 0) === 0}
            error={reportsQuery.error}
            isError={reportsQuery.isError}
            isLoading={reportsQuery.isLoading}
            onRetry={() => void reportsQuery.refetch()}
          >
            <StatusBarChart data={statusChartData(reportsQuery.data?.status_counts)} />
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, mt: 2 }}>
              {Object.keys(reportsQuery.data?.status_counts ?? {}).map((status) => (
                <Button
                  key={status}
                  onClick={() => replaceSearchParams({ offset: 0, statusCode: status })}
                  size="small"
                  variant={search.statusCode === status ? 'contained' : 'outlined'}
                >
                  {status}
                </Button>
              ))}
            </Stack>
          </QueryState>
        </CardContent>
      </Card>

      <Card variant="outlined">
        <CardContent>
          <Typography component="h2" sx={{ mb: 2 }} variant="h3">
            Report entries
          </Typography>
          <FilterToolbar>
            <TextField
              fullWidth
              label="Search reports"
              onChange={(event) => replaceSearchParams({ offset: 0, q: event.target.value })}
              size="small"
              value={search.q ?? ''}
            />
            <TextField
              label="Operation"
              onChange={(event) => replaceSearchParams({ offset: 0, operationId: event.target.value })}
              size="small"
              sx={{ minWidth: 220 }}
              value={search.operationId ?? ''}
            />
            <TextField
              label="Status"
              onChange={(event) => replaceSearchParams({ offset: 0, statusCode: event.target.value })}
              size="small"
              sx={{ minWidth: 120 }}
              value={search.statusCode ?? ''}
            />
            <TextField
              label="Group"
              onChange={(event) => replaceSearchParams({ groupBy: event.target.value, offset: 0 })}
              select
              size="small"
              sx={{ minWidth: 160 }}
              value={search.groupBy ?? ''}
            >
              <MenuItem value="">No grouping</MenuItem>
              <MenuItem value="operation_id">Operation</MenuItem>
              <MenuItem value="status_code">Status</MenuItem>
            </TextField>
          </FilterToolbar>
          <ActiveFilterChips
            filters={[
              { key: 'q', label: 'Search', value: search.q },
              { key: 'operationId', label: 'Operation', value: search.operationId },
              { key: 'statusCode', label: 'Status', value: search.statusCode },
              { key: 'groupBy', label: 'Group', value: search.groupBy },
            ]}
          />
          <QueryState
            empty={rows.length === 0}
            error={entriesQuery.error}
            isError={entriesQuery.isError}
            isLoading={entriesQuery.isLoading}
            onRetry={() => void entriesQuery.refetch()}
          >
            <ServerDataGridPanel
              ariaLabel="report entries"
              columns={reportColumns}
              getRowId={(row) => row.id}
              loading={entriesQuery.isFetching}
              onPaginationModelChange={gridState.handlePaginationModelChange}
              onSortModelChange={gridState.handleSortModelChange}
              paginationModel={gridState.paginationModel}
              rowCount={entriesQuery.data?.pagination.total ?? 0}
              rows={rows}
              sortModel={gridState.sortModel}
            />
          </QueryState>
        </CardContent>
      </Card>
      <OperationDetailDrawer operationId={search.operationId} runName={runName} />
      <ExportSnapshotDialog
        data={{ entries: rows, status_counts: reportsQuery.data?.status_counts }}
        filters={search}
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={`/runs/${encodeURIComponent(runName)}/reports`}
        title="Reports"
      />
    </Stack>
  )
}
