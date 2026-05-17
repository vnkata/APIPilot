import DownloadIcon from '@mui/icons-material/Download'
import {
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useCallback, useMemo, useState } from 'react'

import type { OperationExplorerEntryResponse, SortOrder } from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { EvidenceSummaryCard } from '../../shared/ui/EvidenceSummaryCard'
import { EvidenceLinkSet } from '../../shared/ui/EvidenceLinkSet'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FacetFilterBar, type FacetFilter } from '../../shared/ui/FacetFilterBar'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { RawFieldsAccordion } from '../../shared/ui/RawFieldsAccordion'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { StatusSignalStrip } from '../../shared/ui/StatusSignalStrip'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { ViewModeToggle } from '../../shared/ui/ViewModeToggle'
import {
  toOperationExplorerParams,
  toOperationFacetParams,
  useOperationExplorerDetail,
  useOperationExplorerEntries,
  useOperationExplorerFacets,
} from './api'
import {
  buildOperationMissionBoard,
  summarizeOperationDetail,
} from './operationViewModels'

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
  operationsView?: 'cards' | 'canvas' | 'table'
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

function OperationEvidenceBadges({ operation }: { operation: OperationExplorerEntryResponse }) {
  return (
    <>
      <Chip label={operation.http_method?.toUpperCase() ?? 'UNKNOWN'} size="small" />
      <Chip label={operation.response_statuses.join(', ')} size="small" variant="outlined" />
      <Chip label={`${operation.constraint_count} constraints`} size="small" variant="outlined" />
      <Chip label={`${operation.invariant_count} invariants`} size="small" variant="outlined" />
      <Chip label={`${operation.test_case_count} test cases`} size="small" variant="outlined" />
      <Chip label={`${operation.graph_in_degree} in / ${operation.graph_out_degree} out`} size="small" variant="outlined" />
    </>
  )
}

function OperationCard({
  onSelect,
  operation,
}: {
  onSelect: (operationKey: string) => void
  operation: OperationExplorerEntryResponse
}) {
  return (
    <EvidenceSummaryCard
      actionLabel={operation.display_operation_id ?? operation.operation_id}
      badges={<OperationEvidenceBadges operation={operation} />}
      description={operation.path_template}
      metric={operation.has_failures ? 'Failures' : 'Clean'}
      onAction={() => onSelect(operation.operation_key)}
      title={operation.operation_id}
      tone={operation.has_failures ? 'danger' : 'success'}
    />
  )
}

function OperationCardsView({
  onSelect,
  rows,
}: {
  onSelect: (operationKey: string) => void
  rows: OperationExplorerEntryResponse[]
}) {
  return (
    <Grid aria-label="Operation cards" component="section" container role="region" spacing={2}>
      {rows.map((operation) => (
        <Grid key={operation.operation_key} size={{ xs: 12, md: 6, xl: 4 }}>
          <OperationCard onSelect={onSelect} operation={operation} />
        </Grid>
      ))}
    </Grid>
  )
}

function OperationEvidenceCanvas({
  onSelect,
  rows,
}: {
  onSelect: (operationKey: string) => void
  rows: OperationExplorerEntryResponse[]
}) {
  const board = buildOperationMissionBoard(rows)

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' } }}>
        <Stack spacing={0.5} sx={{ flex: 1 }}>
          <Typography component="h2" variant="h2">
            Operation Mission Board
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Triage the visible server-paginated result set by failures, dependency pressure, constraints, and evidence readiness.
          </Typography>
        </Stack>
        <StatusSignalStrip
          ariaLabel="Operation evidence signals"
          signals={[
            { label: 'Failures', tone: board.metrics.failures > 0 ? 'danger' : 'success', value: board.metrics.failures },
            { label: 'Graph linked', tone: board.metrics.graphLinked > 0 ? 'success' : 'neutral', value: board.metrics.graphLinked },
            { label: 'Low evidence', tone: board.metrics.lowEvidence > 0 ? 'warning' : 'success', value: board.metrics.lowEvidence },
            { label: 'Visible', value: board.metrics.visible },
          ]}
        />
      </Stack>

      <Grid container spacing={2}>
        {board.lanes.map((lane) => (
          <Grid key={lane.id} size={{ xs: 12, lg: lane.id === 'failures' ? 12 : 6, xl: 4 }}>
            <Card variant="outlined" sx={{ height: '100%' }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Stack spacing={0.5}>
                    <Typography component="h3" variant="h3">
                      {lane.title}
                    </Typography>
                    <Typography color="text.secondary" variant="body2">
                      {lane.description}
                    </Typography>
                  </Stack>
                  {lane.operations.length > 0 ? (
                    lane.operations.map((operation) => (
                      <OperationCard key={operation.operation_key} onSelect={onSelect} operation={operation} />
                    ))
                  ) : (
                    <Typography color="text.secondary" variant="body2">
                      No visible operations in this lane.
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  )
}

export function OperationsPage({ runName, search }: OperationsPageProps) {
  const [exportOpen, setExportOpen] = useState(false)
  const [localOperationKey, setLocalOperationKey] = useState<string>()
  const encodedRunName = encodeRoutePart(runName)
  const operationsView = search.operationsView ?? 'table'
  const gridState = useUrlBackedGridState(search)
  const params = toOperationExplorerParams(search)
  const facetParams = toOperationFacetParams(search)
  const entriesQuery = useOperationExplorerEntries(runName, params)
  const facetsQuery = useOperationExplorerFacets(runName, facetParams)
  const selectedOperationKey = search.operationKey ?? localOperationKey
  const detailOpen = Boolean(selectedOperationKey)
  const detailQuery = useOperationExplorerDetail(
    runName,
    selectedOperationKey ?? '',
    { query: { enabled: detailOpen } },
  )

  const selectOperation = useCallback((operationKey: string) => {
    setLocalOperationKey(operationKey)
    replaceSearchParams({ operationKey })
  }, [])

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
              selectOperation(params.row.operation_key)
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
    [selectOperation],
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
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
            <ViewModeToggle
              ariaLabel="Operations view mode"
              onChange={(value) => replaceSearchParams({ operationsView: value })}
              options={[
                { description: 'Current server-paginated table.', label: 'Table', value: 'table' },
                { description: 'Evidence-rich QA canvas.', label: 'Canvas', value: 'canvas' },
                { description: 'Compact responsive triage cards.', label: 'Cards', value: 'cards' },
              ]}
              value={operationsView}
            />
            <Button onClick={() => setExportOpen(true)} startIcon={<DownloadIcon />} variant="outlined">
              Export snapshot
            </Button>
          </Stack>
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
              {operationsView === 'canvas' ? (
                <OperationEvidenceCanvas onSelect={selectOperation} rows={rows} />
              ) : operationsView === 'cards' ? (
                <OperationCardsView onSelect={selectOperation} rows={rows} />
              ) : (
                <ServerDataGridPanel
                  ariaLabel="operation explorer entries"
                  columns={columns}
                  getRowId={(row) => row.operation_key}
                  loading={entriesQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onRowClick={(params) => selectOperation(params.row.operation_key)}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={entriesQuery.data?.pagination.total ?? 0}
                  rows={rows}
                  sortModel={gridState.sortModel}
                />
              )}
            </QueryState>
          </Stack>
        </CardContent>
      </Card>

      <InvestigationDrawer
        ariaLabel="Operation explorer detail"
        error={detailQuery.error}
        isError={detailQuery.isError}
        isLoading={detailQuery.isLoading}
        onClose={() => {
          setLocalOperationKey(undefined)
          replaceSearchParams({ operationKey: undefined })
        }}
        onRetry={() => void detailQuery.refetch()}
        open={detailOpen}
        subtitle={selectedOperationKey}
        title="Operation explorer detail"
      >
        {detailQuery.data ? (
          (() => {
            const summary = summarizeOperationDetail(detailQuery.data)
            return (
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
                <Stack spacing={1}>
                  <Typography component="h4" variant="subtitle2">
                    Related evidence
                  </Typography>
                  {summary.relatedGroups.map((group) => (
                    <Stack key={group.label} spacing={0.75}>
                      <Typography color="text.secondary" variant="caption">
                        {group.label}
                      </Typography>
                      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                        {group.values.length > 0 ? (
                          group.values.map((value) => (
                            <Chip key={value} label={value} size="small" variant="outlined" />
                          ))
                        ) : (
                          <Chip label="None visible" size="small" variant="outlined" />
                        )}
                      </Stack>
                    </Stack>
                  ))}
                </Stack>
                <Stack spacing={1}>
                  <Typography component="h4" variant="subtitle2">
                    Parameters
                  </Typography>
                  {summary.parameterItems.length > 0 ? (
                    summary.parameterItems.map((parameter) => (
                      <Card key={parameter.name} variant="outlined">
                        <CardContent>
                          <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                            <Chip label={parameter.location} size="small" />
                            <Typography sx={{ fontWeight: 800 }}>{parameter.name}</Typography>
                            <Typography color="text.secondary" variant="body2">
                              {parameter.summary}
                            </Typography>
                          </Stack>
                        </CardContent>
                      </Card>
                    ))
                  ) : (
                    <Typography color="text.secondary" variant="body2">
                      No parameters visible for this operation.
                    </Typography>
                  )}
                </Stack>
                <Stack spacing={1}>
                  <Typography component="h4" variant="subtitle2">
                    Responses
                  </Typography>
                  {summary.responseItems.map((response) => (
                    <Card key={response.status} variant="outlined">
                      <CardContent>
                        <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                          <Chip label={response.status} size="small" />
                          <Typography color="text.secondary" variant="body2">
                            {response.summary}
                          </Typography>
                        </Stack>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
                <RawFieldsAccordion value={summary.raw} />
              </Stack>
            )
          })()
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
