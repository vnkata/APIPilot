import DownloadIcon from '@mui/icons-material/Download'
import {
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useMemo, useState } from 'react'

import type { OperationExplorerEntryResponse, SortOrder } from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { EvidenceLinkSet } from '../../shared/ui/EvidenceLinkSet'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FacetFilterBar, type FacetFilter } from '../../shared/ui/FacetFilterBar'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import {
  toOperationExplorerParams,
  toOperationFacetParams,
  useOperationExplorerDetail,
  useOperationExplorerEntries,
  useOperationExplorerFacets,
} from './api'

export type OperationsPageSearch = {
  groupBy?: string
  hasConstraints?: boolean
  hasFailures?: boolean
  hasGraphEdges?: boolean
  hasInvariants?: boolean
  hasRequestBody?: boolean
  httpMethod?: string
  limit: number
  offset: number
  operationId?: string
  operationKey?: string
  q?: string
  responseStatus?: string
  sortBy?: string
  sortOrder?: SortOrder
}

type OperationsPageProps = {
  runName: string
  search: OperationsPageSearch
}

function booleanSelectValue(value: boolean | undefined) {
  if (value === undefined) return ''
  return value ? 'true' : 'false'
}

function selectedBoolean(value: boolean | undefined) {
  if (value === undefined) return undefined
  return String(value)
}

function toBooleanSearchValue(value: string) {
  return value === '' ? undefined : value
}

function statusColor(hasFailures: boolean) {
  return hasFailures ? 'error' : 'success'
}

export function OperationsPage({ runName, search }: OperationsPageProps) {
  const [exportOpen, setExportOpen] = useState(false)
  const encodedRunName = encodeRoutePart(runName)
  const gridState = useUrlBackedGridState(search)
  const params = toOperationExplorerParams(search)
  const facetParams = toOperationFacetParams(search)
  const entriesQuery = useOperationExplorerEntries(runName, params)
  const facetsQuery = useOperationExplorerFacets(runName, facetParams)
  const detailOpen = Boolean(search.operationKey)
  const detailQuery = useOperationExplorerDetail(
    runName,
    search.operationKey ?? '',
    { query: { enabled: detailOpen } },
  )

  const rows = entriesQuery.data?.items ?? []
  const columns = useMemo<GridColDef<OperationExplorerEntryResponse>[]>(
    () => [
      {
        field: 'operation_id',
        flex: 1.2,
        headerName: 'Operation',
        minWidth: 180,
        renderCell: (params) => (
          <Button
            color="inherit"
            onClick={(event) => {
              event.stopPropagation()
              replaceSearchParams({ operationKey: params.row.operation_key })
            }}
            size="small"
          >
            {params.row.operation_id}
          </Button>
        ),
      },
      { field: 'http_method', headerName: 'Method', minWidth: 96 },
      { field: 'path_template', flex: 1, headerName: 'Path', minWidth: 160 },
      {
        field: 'response_statuses',
        flex: 0.9,
        headerName: 'Statuses',
        minWidth: 160,
        valueGetter: (_value, row) => row.response_statuses.join(', '),
      },
      { field: 'constraint_count', headerName: 'Constraints', minWidth: 120 },
      { field: 'invariant_count', headerName: 'Invariants', minWidth: 120 },
      { field: 'test_case_count', headerName: 'Test cases', minWidth: 120 },
      {
        field: 'has_failures',
        headerName: 'Risk',
        minWidth: 120,
        renderCell: (params) => (
          <Chip
            color={statusColor(params.row.has_failures)}
            label={params.row.has_failures ? 'Failures' : 'Clean'}
            size="small"
            variant={params.row.has_failures ? 'filled' : 'outlined'}
          />
        ),
      },
    ],
    [],
  )

  const facets = facetsQuery.data
  const facetFilters: FacetFilter[] = [
    {
      buckets: facets?.http_method,
      label: 'Method',
      onSelect: (value) => replaceSearchParams({ httpMethod: value, offset: 0 }),
      selectedValue: search.httpMethod,
    },
    {
      buckets: facets?.has_failures,
      label: 'Failures',
      onSelect: (value) => replaceSearchParams({ hasFailures: value, offset: 0 }),
      selectedValue: selectedBoolean(search.hasFailures),
    },
    {
      buckets: facets?.has_constraints,
      label: 'Constraints',
      onSelect: (value) => replaceSearchParams({ hasConstraints: value, offset: 0 }),
      selectedValue: selectedBoolean(search.hasConstraints),
    },
    {
      buckets: facets?.has_invariants,
      label: 'Invariants',
      onSelect: (value) => replaceSearchParams({ hasInvariants: value, offset: 0 }),
      selectedValue: selectedBoolean(search.hasInvariants),
    },
    {
      buckets: facets?.has_graph_edges,
      label: 'Graph edges',
      onSelect: (value) => replaceSearchParams({ hasGraphEdges: value, offset: 0 }),
      selectedValue: selectedBoolean(search.hasGraphEdges),
    },
    {
      buckets: facets?.response_status,
      label: 'Status',
      onSelect: (value) => replaceSearchParams({ responseStatus: value, offset: 0 }),
      selectedValue: search.responseStatus,
    },
  ]

  const operationId = detailQuery.data?.operation_id ?? search.operationId
  const encodedOperationId = encodeURIComponent(operationId ?? '')
  const evidenceLinks = operationId
    ? [
        { href: `/runs/${encodedRunName}/graph?operationId=${encodedOperationId}`, label: 'Graph' },
        { href: `/runs/${encodedRunName}/constraints?constraintTab=explorer&operationId=${encodedOperationId}`, label: 'Constraints' },
        { href: `/runs/${encodedRunName}/test-cases?operationId=${encodedOperationId}`, label: 'Test cases' },
        { href: `/runs/${encodedRunName}/reports?operationId=${encodedOperationId}`, label: 'Reports' },
      ]
    : []

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Button onClick={() => setExportOpen(true)} startIcon={<DownloadIcon />} variant="outlined">
            Export snapshot
          </Button>
        }
        eyebrow="Investigation hub"
        subtitle="Triage operations by failures, evidence coverage, graph links, constraints, invariants, and test cases."
        title="Operations Explorer"
      />

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <FilterToolbar>
              <TextField
                fullWidth
                label="Search operations"
                onChange={(event) => replaceSearchParams({ offset: 0, q: event.target.value })}
                size="small"
                value={search.q ?? ''}
              />
              <TextField
                label="Status"
                onChange={(event) => replaceSearchParams({ offset: 0, responseStatus: event.target.value })}
                size="small"
                sx={{ minWidth: 120 }}
                value={search.responseStatus ?? ''}
              />
              <TextField
                label="Failures"
                onChange={(event) => replaceSearchParams({ hasFailures: toBooleanSearchValue(event.target.value), offset: 0 })}
                select
                size="small"
                sx={{ minWidth: 140 }}
                value={booleanSelectValue(search.hasFailures)}
              >
                <MenuItem value="">Any</MenuItem>
                <MenuItem value="true">Has failures</MenuItem>
                <MenuItem value="false">No failures</MenuItem>
              </TextField>
              <TextField
                label="Group"
                onChange={(event) => replaceSearchParams({ groupBy: event.target.value, offset: 0 })}
                select
                size="small"
                sx={{ minWidth: 180 }}
                value={search.groupBy ?? ''}
              >
                <MenuItem value="">No grouping</MenuItem>
                <MenuItem value="http_method">Method</MenuItem>
                <MenuItem value="has_failures">Failures</MenuItem>
                <MenuItem value="has_constraints">Constraints</MenuItem>
                <MenuItem value="has_invariants">Invariants</MenuItem>
                <MenuItem value="has_graph_edges">Graph edges</MenuItem>
              </TextField>
            </FilterToolbar>

            <FacetFilterBar filters={facetFilters} />

            <ActiveFilterChips
              filters={[
                { key: 'q', label: 'Search', value: search.q },
                { key: 'httpMethod', label: 'Method', value: search.httpMethod },
                { key: 'responseStatus', label: 'Status', value: search.responseStatus },
                { key: 'hasFailures', label: 'Failures', value: search.hasFailures },
                { key: 'hasConstraints', label: 'Constraints', value: search.hasConstraints },
                { key: 'hasInvariants', label: 'Invariants', value: search.hasInvariants },
                { key: 'hasGraphEdges', label: 'Graph edges', value: search.hasGraphEdges },
                { key: 'groupBy', label: 'Group', value: search.groupBy },
                { key: 'operationKey', label: 'Selected', value: search.operationKey },
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
                ariaLabel="operation explorer entries"
                columns={columns}
                getRowId={(row) => row.operation_key}
                loading={entriesQuery.isFetching}
                onPaginationModelChange={gridState.handlePaginationModelChange}
                onRowClick={(params) => replaceSearchParams({ operationKey: params.row.operation_key })}
                onSortModelChange={gridState.handleSortModelChange}
                paginationModel={gridState.paginationModel}
                rowCount={entriesQuery.data?.pagination.total ?? 0}
                rows={rows}
                sortModel={gridState.sortModel}
              />
            </QueryState>
          </Stack>
        </CardContent>
      </Card>

      <InvestigationDrawer
        ariaLabel="Operation explorer detail"
        error={detailQuery.error}
        isError={detailQuery.isError}
        isLoading={detailQuery.isLoading}
        onClose={() => replaceSearchParams({ operationKey: undefined })}
        onRetry={() => void detailQuery.refetch()}
        open={detailOpen}
        subtitle={search.operationKey}
        title="Operation explorer detail"
      >
        {detailQuery.data ? (
          <Stack spacing={2}>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip label={detailQuery.data.http_method?.toUpperCase() ?? 'UNKNOWN'} size="small" />
              <Chip label={detailQuery.data.path_template ?? detailQuery.data.operation_id} size="small" variant="outlined" />
              <Chip color={statusColor(detailQuery.data.has_failures)} label={detailQuery.data.has_failures ? 'Has failures' : 'No failures'} size="small" />
            </Stack>
            <Typography component="h3" variant="h3">
              {detailQuery.data.display_operation_id ?? detailQuery.data.operation_id}
            </Typography>
            <EvidenceLinkSet links={evidenceLinks} />
            <Divider />
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip label={`${detailQuery.data.constraint_count} constraints`} size="small" />
              <Chip label={`${detailQuery.data.invariant_count} invariants`} size="small" />
              <Chip label={`${detailQuery.data.test_case_count} test cases`} size="small" />
              <Chip label={`${detailQuery.data.graph_in_degree} in / ${detailQuery.data.graph_out_degree} out`} size="small" />
            </Stack>
            <Typography component="h4" variant="subtitle2">
              Related IDs
            </Typography>
            <JsonBlock maxHeight={180} value={{
              incoming_edge_ids: detailQuery.data.incoming_edge_ids,
              outgoing_edge_ids: detailQuery.data.outgoing_edge_ids,
              related_constraint_ids: detailQuery.data.related_constraint_ids,
              related_invariant_ids: detailQuery.data.related_invariant_ids,
            }} />
            <Typography component="h4" variant="subtitle2">
              Parameters
            </Typography>
            <JsonBlock maxHeight={180} value={detailQuery.data.parameters} />
            <Typography component="h4" variant="subtitle2">
              Responses
            </Typography>
            <JsonBlock maxHeight={220} value={detailQuery.data.responses} />
          </Stack>
        ) : null}
      </InvestigationDrawer>

      <ExportSnapshotDialog
        data={rows}
        filters={search}
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={`/runs/${encodedRunName}/operations`}
        selectedContext={detailQuery.data}
        title="Operations Explorer"
      />
    </Stack>
  )
}
