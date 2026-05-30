import { useMemo, useState } from 'react'
import {
  Button,
  Card,
  CardContent,
  Grid,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'

import type { StatusReportEntryResponse } from '../../shared/api/generated/model'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { DebouncedTextField } from '../../shared/ui/DebouncedTextField'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { MetricCard } from '../../shared/ui/MetricCard'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { StatusCodeBadge } from '../../shared/ui/SemanticBadges'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
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

function statusGroup(status: string) {
  if (status.startsWith('2')) return 'Success'
  if (status.startsWith('3')) return 'Redirect'
  if (status.startsWith('4')) return 'Client risk'
  if (status.startsWith('5')) return 'Server risk'
  return 'Unknown'
}

function StatusDistributionTable({ statusCounts }: { statusCounts: Record<string, number> | undefined }) {
  const rows = Object.entries(statusCounts ?? {}).sort(([left], [right]) => Number(left) - Number(right))

  if (rows.length === 0) return null

  return (
    <TableContainer sx={{ mt: 2 }}>
      <Table aria-label="status distribution summary" size="small">
        <TableHead>
          <TableRow>
            <TableCell>Status</TableCell>
            <TableCell>Group</TableCell>
            <TableCell align="right">Count</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(([status, count]) => (
            <TableRow key={status}>
              <TableCell>
                <StatusCodeBadge statusCode={status} />
              </TableCell>
              <TableCell>{statusGroup(status)}</TableCell>
              <TableCell align="right">{count}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
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
  const statusCounts = reportsQuery.data?.status_counts
  const statusRows = statusChartData(statusCounts)
  const totalStatusCount = statusRows.reduce((total, item) => total + item.count, 0)
  const riskStatusCount = statusRows
    .filter((item) => item.status.startsWith('4') || item.status.startsWith('5'))
    .reduce((total, item) => total + item.count, 0)
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
      {
        field: 'status_code',
        flex: 0.8,
        headerName: 'Status',
        minWidth: 150,
        renderCell: (params) => <StatusCodeBadge statusCode={params.row.status_code} />,
      },
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
        subtitle="Analyze APIPilot Artifact Command Center status distribution and operation risk concentration."
        {...tourAnchor(TOUR_ANCHORS.reportsHeader)}
      />

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 3 }}>
          <MetricCard
            label="Report entries"
            value={reportsQuery.data?.entries.length ?? 0}
            caption="Loaded from /reports"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <MetricCard
            label="Paginated rows"
            value={entriesQuery.data?.pagination.total ?? 0}
            caption="Loaded from /reports/entries"
          />
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <MetricCard
            label="Distinct statuses"
            value={Object.keys(statusCounts ?? {}).length}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <MetricCard
            caption={totalStatusCount > 0 ? `${Math.round((riskStatusCount / totalStatusCount) * 100)}% of visible status events` : 'No status events loaded'}
            label="4xx/5xx risk"
            value={riskStatusCount}
          />
        </Grid>
      </Grid>

      <Card variant="outlined" {...tourAnchor(TOUR_ANCHORS.reportsStatusDistribution)}>
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
            <StatusBarChart data={statusRows} />
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, mt: 2 }}>
              {Object.entries(statusCounts ?? {}).map(([status, count]) => (
                <Button
                  aria-label={`Filter reports by ${status} status with ${count} entries`}
                  key={status}
                  onClick={() => replaceSearchParams({ offset: 0, statusCode: status })}
                  size="small"
                  variant={search.statusCode === status ? 'contained' : 'outlined'}
                >
                  <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                    <StatusCodeBadge statusCode={status} />
                    <Typography component="span" variant="caption">
                      {count}
                    </Typography>
                  </Stack>
                </Button>
              ))}
            </Stack>
            <StatusDistributionTable statusCounts={statusCounts} />
          </QueryState>
        </CardContent>
      </Card>

      <Card variant="outlined" {...tourAnchor(TOUR_ANCHORS.reportsResults)}>
        <CardContent>
          <Typography component="h2" sx={{ mb: 2 }} variant="h3">
            Report entries
          </Typography>
          <FilterToolbar>
            <DebouncedTextField
              fullWidth
              label="Search reports"
              onDebouncedChange={(value) => replaceSearchParams({ offset: 0, q: value })}
              size="small"
              value={search.q ?? ''}
            />
            <DebouncedTextField
              label="Operation"
              onDebouncedChange={(value) => replaceSearchParams({ offset: 0, operationId: value })}
              size="small"
              sx={{ minWidth: 220 }}
              value={search.operationId ?? ''}
            />
            <DebouncedTextField
              label="Status"
              onDebouncedChange={(value) => replaceSearchParams({ offset: 0, statusCode: value })}
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
