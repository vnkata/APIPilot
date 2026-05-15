import DownloadIcon from '@mui/icons-material/Download'
import {
  Button,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useMemo, useState } from 'react'

import type {
  ConstraintEntryDetailResponse,
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
  SortOrder,
} from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { EvidenceLinkSet } from '../../shared/ui/EvidenceLinkSet'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FacetFilterBar, type FacetFilter } from '../../shared/ui/FacetFilterBar'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import {
  toConstraintExplorerParams,
  toConstraintFacetParams,
  toInvariantExplorerParams,
  toInvariantFacetParams,
  useConstraintExplorerDetail,
  useConstraintExplorerEntries,
  useConstraintExplorerFacets,
  useDynamicConstraintEntries,
  useDynamicConstraintsSummary,
  useInvariantExplorerDetail,
  useInvariantExplorerEntries,
  useInvariantExplorerFacets,
  useStaticConstraintEntries,
  useStaticConstraintsSummary,
} from './api'

export type ConstraintTab = 'dynamic' | 'explorer' | 'invariants' | 'static'

export type ConstraintsPageSearch = {
  agreementStatus?: string
  assertionAvailable?: boolean
  constraintId?: string
  constraintKind?: string
  constraintTab: ConstraintTab
  correlationConfidence?: string
  groupBy?: string
  invariantId?: string
  invariantKind?: string
  invariantType?: string
  limit: number
  offset: number
  operationId?: string
  oracleReadiness?: string
  propertyPath?: string
  propertyPrefix?: string
  q?: string
  section?: string
  sortBy?: string
  sortOrder?: SortOrder
  source?: string
  sourceType?: string
}

type ConstraintsPageProps = {
  runName: string
  search: ConstraintsPageSearch
}

type LegacyConstraintRow = ConstraintEntryDetailResponse & { id: string }

function constraintRows(items: ConstraintEntryDetailResponse[]) {
  return items.map((item, index) => ({
    ...item,
    id: `${item.operation_id}:${item.section ?? 'dynamic'}:${item.property_path}:${index}`,
  }))
}

function booleanSelectValue(value: boolean | undefined) {
  if (value === undefined) return ''
  return value ? 'true' : 'false'
}

function booleanSearchValue(value: string) {
  return value === '' ? undefined : value
}

function selectedBoolean(value: boolean | undefined) {
  if (value === undefined) return undefined
  return String(value)
}

export function ConstraintsPage({ runName, search }: ConstraintsPageProps) {
  const [legacyDetail, setLegacyDetail] = useState<LegacyConstraintRow | null>(null)
  const [exportOpen, setExportOpen] = useState(false)
  const encodedRunName = encodeRoutePart(runName)
  const gridState = useUrlBackedGridState(search)
  const tab = search.constraintTab ?? 'explorer'
  const staticSummaryQuery = useStaticConstraintsSummary(runName)
  const dynamicSummaryQuery = useDynamicConstraintsSummary(runName)
  const explorerParams = toConstraintExplorerParams(search)
  const explorerFacetParams = toConstraintFacetParams(search)
  const invariantParams = toInvariantExplorerParams(search)
  const invariantFacetParams = toInvariantFacetParams(search)

  const explorerQuery = useConstraintExplorerEntries(runName, explorerParams, { query: { enabled: tab === 'explorer' } })
  const explorerFacetsQuery = useConstraintExplorerFacets(runName, explorerFacetParams, { query: { enabled: tab === 'explorer' } })
  const constraintDetailOpen = Boolean(search.constraintId)
  const constraintDetailQuery = useConstraintExplorerDetail(
    runName,
    search.constraintId ?? '',
    { query: { enabled: constraintDetailOpen } },
  )
  const invariantExplorerQuery = useInvariantExplorerEntries(runName, invariantParams, { query: { enabled: tab === 'invariants' } })
  const invariantFacetsQuery = useInvariantExplorerFacets(runName, invariantFacetParams, { query: { enabled: tab === 'invariants' } })
  const invariantDetailOpen = Boolean(search.invariantId)
  const invariantDetailQuery = useInvariantExplorerDetail(
    runName,
    search.invariantId ?? '',
    { query: { enabled: invariantDetailOpen } },
  )
  const staticEntriesQuery = useStaticConstraintEntries(runName, {
    group_by: search.groupBy,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    q: search.q,
    section: search.section,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
  }, { query: { enabled: tab === 'static' } })
  const dynamicEntriesQuery = useDynamicConstraintEntries(runName, {
    group_by: search.groupBy,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    q: search.q,
    section: search.section,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
  }, { query: { enabled: tab === 'dynamic' } })

  const legacyConstraintRows = useMemo(
    () => constraintRows((tab === 'dynamic' ? dynamicEntriesQuery.data?.items : staticEntriesQuery.data?.items) ?? []),
    [dynamicEntriesQuery.data?.items, staticEntriesQuery.data?.items, tab],
  )
  const explorerRows = explorerQuery.data?.items ?? []
  const invariantRowsNew = invariantExplorerQuery.data?.items ?? []
  const legacyQuery = tab === 'dynamic' ? dynamicEntriesQuery : staticEntriesQuery
  const activeGroups =
    tab === 'explorer'
      ? explorerQuery.data?.groups ?? []
      : tab === 'invariants'
        ? invariantExplorerQuery.data?.groups ?? []
        : legacyQuery.data?.groups ?? []
  const activeRows =
    tab === 'explorer'
      ? explorerRows
      : tab === 'invariants'
        ? invariantRowsNew
        : legacyConstraintRows

  const explorerColumns = useMemo<GridColDef<ConstraintExplorerEntryResponse>[]>(
    () => [
      {
        field: 'operation_id',
        flex: 1,
        headerName: 'Operation',
        minWidth: 160,
        renderCell: (params) => (
          <Button onClick={() => replaceSearchParams({ operationId: params.row.operation_id })} size="small">
            {params.row.operation_id}
          </Button>
        ),
      },
      { field: 'source', headerName: 'Source', minWidth: 120 },
      { field: 'constraint_kind', headerName: 'Kind', minWidth: 160 },
      { field: 'agreement_status', headerName: 'Agreement', minWidth: 160 },
      { field: 'property_path', flex: 1, headerName: 'Property path', minWidth: 180 },
      {
        field: 'expression',
        flex: 1.4,
        headerName: 'Expression',
        minWidth: 260,
        renderCell: (params) => (
          <Button color="inherit" onClick={() => replaceSearchParams({ constraintId: params.row.constraint_id })} size="small">
            {params.row.expression}
          </Button>
        ),
      },
    ],
    [],
  )
  const invariantColumns = useMemo<GridColDef<InvariantExplorerEntryResponse>[]>(
    () => [
      {
        field: 'operation_id',
        flex: 1,
        headerName: 'Operation',
        minWidth: 160,
        renderCell: (params) =>
          params.row.operation_id ? (
            <Button onClick={() => replaceSearchParams({ operationId: params.row.operation_id })} size="small">
              {params.row.operation_id}
            </Button>
          ) : null,
      },
      { field: 'invariant_kind', headerName: 'Kind', minWidth: 140 },
      { field: 'oracle_readiness', headerName: 'Oracle readiness', minWidth: 200 },
      { field: 'correlation_confidence', headerName: 'Correlation', minWidth: 160 },
      {
        field: 'invariant',
        flex: 1.5,
        headerName: 'Invariant',
        minWidth: 260,
        renderCell: (params) => (
          <Button color="inherit" onClick={() => replaceSearchParams({ invariantId: params.row.invariant_id })} size="small">
            {params.row.invariant ?? params.row.invariant_id}
          </Button>
        ),
      },
      { field: 'assertion_preview', flex: 1.4, headerName: 'Assertion', minWidth: 240 },
    ],
    [],
  )
  const legacyConstraintColumns = useMemo<GridColDef<LegacyConstraintRow>[]>(
    () => [
      {
        field: 'operation_id',
        flex: 1,
        headerName: 'Operation',
        minWidth: 160,
        renderCell: (params) => (
          <Button onClick={() => replaceSearchParams({ operationId: params.row.operation_id })} size="small">
            {params.row.operation_id}
          </Button>
        ),
      },
      { field: 'section', flex: 0.8, headerName: 'Section', minWidth: 160 },
      { field: 'property_path', flex: 1.1, headerName: 'Property path', minWidth: 200 },
      {
        field: 'expression',
        flex: 1.8,
        headerName: 'Expression',
        minWidth: 280,
        renderCell: (params) => (
          <Button color="inherit" onClick={() => setLegacyDetail(params.row)} size="small">
            {params.row.expression}
          </Button>
        ),
      },
    ],
    [],
  )

  function switchTab(value: ConstraintTab) {
    replaceSearchParams({
      constraintId: undefined,
      constraintTab: value,
      invariantId: undefined,
      offset: 0,
    })
  }

  function applyGroupFilter(key: string | null | undefined) {
    if (!key) return
    if (search.groupBy === 'operation_id') replaceSearchParams({ offset: 0, operationId: key })
    if (search.groupBy === 'section') replaceSearchParams({ offset: 0, section: key })
    if (search.groupBy === 'source') replaceSearchParams({ offset: 0, source: key })
    if (search.groupBy === 'constraint_kind') replaceSearchParams({ constraintKind: key, offset: 0 })
    if (search.groupBy === 'agreement_status') replaceSearchParams({ agreementStatus: key, offset: 0 })
    if (search.groupBy === 'invariant_kind') replaceSearchParams({ invariantKind: key, offset: 0 })
    if (search.groupBy === 'invariant_type') replaceSearchParams({ invariantType: key, offset: 0 })
    if (search.groupBy === 'oracle_readiness') replaceSearchParams({ offset: 0, oracleReadiness: key })
  }

  const constraintFacets = explorerFacetsQuery.data
  const invariantFacets = invariantFacetsQuery.data
  const facetFilters: FacetFilter[] = tab === 'invariants'
    ? [
        {
          buckets: invariantFacets?.oracle_readiness,
          label: 'Oracle readiness',
          onSelect: (value) => replaceSearchParams({ offset: 0, oracleReadiness: value }),
          selectedValue: search.oracleReadiness,
        },
        {
          buckets: invariantFacets?.correlation_confidence,
          label: 'Correlation',
          onSelect: (value) => replaceSearchParams({ correlationConfidence: value, offset: 0 }),
          selectedValue: search.correlationConfidence,
        },
        {
          buckets: invariantFacets?.invariant_kind,
          label: 'Invariant kind',
          onSelect: (value) => replaceSearchParams({ invariantKind: value, offset: 0 }),
          selectedValue: search.invariantKind,
        },
      ]
    : [
        {
          buckets: constraintFacets?.source,
          label: 'Source',
          onSelect: (value) => replaceSearchParams({ offset: 0, source: value }),
          selectedValue: search.source,
        },
        {
          buckets: constraintFacets?.agreement_status,
          label: 'Agreement',
          onSelect: (value) => replaceSearchParams({ agreementStatus: value, offset: 0 }),
          selectedValue: search.agreementStatus,
        },
        {
          buckets: constraintFacets?.constraint_kind,
          label: 'Kind',
          onSelect: (value) => replaceSearchParams({ constraintKind: value, offset: 0 }),
          selectedValue: search.constraintKind,
        },
        {
          buckets: constraintFacets?.assertion_available,
          label: 'Assertion',
          onSelect: (value) => replaceSearchParams({ assertionAvailable: value, offset: 0 }),
          selectedValue: selectedBoolean(search.assertionAvailable),
        },
      ]

  const selectedOperationId =
    constraintDetailQuery.data?.operation_id ?? invariantDetailQuery.data?.operation_id ?? search.operationId
  const encodedOperationId = encodeURIComponent(selectedOperationId ?? '')
  const evidenceLinks = selectedOperationId
    ? [
        { href: `/runs/${encodedRunName}/graph?operationId=${encodedOperationId}`, label: 'Graph' },
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
        eyebrow="Constraint oracle workspace"
        subtitle="Explore static, dynamic, combined constraints, and invariant candidates without copying server cache into Redux."
        title="Constraints and invariants"
      />

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                fullWidth
                label="Search constraints"
                onChange={(event) => replaceSearchParams({ offset: 0, q: event.target.value })}
                size="small"
                value={search.q ?? ''}
              />
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Chip label={`Static ${staticSummaryQuery.data?.constraint_count ?? 0}`} size="small" />
                <Chip label={`Dynamic ${dynamicSummaryQuery.data?.constraint_count ?? 0}`} size="small" />
                <Chip label={`Invariants ${dynamicSummaryQuery.data?.invariant_count ?? invariantExplorerQuery.data?.pagination.total ?? 0}`} size="small" />
              </Stack>
            </Stack>

            <Tabs onChange={(_, value: ConstraintTab) => switchTab(value)} value={tab}>
              <Tab label="Explorer" value="explorer" />
              <Tab label="Static" value="static" />
              <Tab label="Dynamic" value="dynamic" />
              <Tab label="Invariants" value="invariants" />
            </Tabs>

            <FilterToolbar>
              <TextField
                label="Operation"
                onChange={(event) => replaceSearchParams({ offset: 0, operationId: event.target.value })}
                size="small"
                sx={{ minWidth: 220 }}
                value={search.operationId ?? ''}
              />
              <TextField
                label="Section"
                onChange={(event) => replaceSearchParams({ offset: 0, section: event.target.value })}
                size="small"
                sx={{ minWidth: 180 }}
                value={search.section ?? ''}
              />
              <TextField
                disabled={tab === 'static' || tab === 'dynamic'}
                label="Source"
                onChange={(event) => replaceSearchParams({ offset: 0, source: event.target.value })}
                select
                size="small"
                sx={{ minWidth: 150 }}
                value={search.source ?? ''}
              >
                <MenuItem value="">Any</MenuItem>
                <MenuItem value="static">Static</MenuItem>
                <MenuItem value="dynamic">Dynamic</MenuItem>
                <MenuItem value="combined">Combined</MenuItem>
              </TextField>
              <TextField
                disabled={tab === 'static' || tab === 'dynamic'}
                label="Kind"
                onChange={(event) =>
                  replaceSearchParams(
                    tab === 'invariants'
                      ? { invariantKind: event.target.value, offset: 0 }
                      : { constraintKind: event.target.value, offset: 0 },
                  )
                }
                size="small"
                sx={{ minWidth: 180 }}
                value={search.constraintKind ?? search.invariantKind ?? ''}
              />
              <TextField
                disabled={tab !== 'explorer'}
                label="Agreement"
                onChange={(event) => replaceSearchParams({ agreementStatus: event.target.value, offset: 0 })}
                size="small"
                sx={{ minWidth: 180 }}
                value={search.agreementStatus ?? ''}
              />
              <TextField
                disabled={tab !== 'invariants'}
                label="Oracle readiness"
                onChange={(event) => replaceSearchParams({ offset: 0, oracleReadiness: event.target.value })}
                size="small"
                sx={{ minWidth: 200 }}
                value={search.oracleReadiness ?? ''}
              />
              <TextField
                label="Assertion"
                onChange={(event) => replaceSearchParams({ assertionAvailable: booleanSearchValue(event.target.value), offset: 0 })}
                select
                size="small"
                sx={{ minWidth: 150 }}
                value={booleanSelectValue(search.assertionAvailable)}
              >
                <MenuItem value="">Any</MenuItem>
                <MenuItem value="true">Available</MenuItem>
                <MenuItem value="false">Missing</MenuItem>
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
                <MenuItem value="source">Source</MenuItem>
                <MenuItem value="operation_id">Operation</MenuItem>
                <MenuItem value="section">Section</MenuItem>
                <MenuItem value="constraint_kind">Constraint kind</MenuItem>
                <MenuItem value="agreement_status">Agreement</MenuItem>
                <MenuItem value="invariant_kind">Invariant kind</MenuItem>
                <MenuItem value="oracle_readiness">Oracle readiness</MenuItem>
              </TextField>
            </FilterToolbar>

            {tab === 'explorer' || tab === 'invariants' ? <FacetFilterBar filters={facetFilters} /> : null}

            <ActiveFilterChips
              filters={[
                { key: 'q', label: 'Search', value: search.q },
                { key: 'operationId', label: 'Operation', value: search.operationId },
                { key: 'section', label: 'Section', value: search.section },
                { key: 'source', label: 'Source', value: search.source },
                { key: 'constraintKind', label: 'Constraint kind', value: search.constraintKind },
                { key: 'agreementStatus', label: 'Agreement', value: search.agreementStatus },
                { key: 'assertionAvailable', label: 'Assertion', value: search.assertionAvailable },
                { key: 'invariantKind', label: 'Invariant kind', value: search.invariantKind },
                { key: 'oracleReadiness', label: 'Oracle readiness', value: search.oracleReadiness },
                { key: 'correlationConfidence', label: 'Correlation', value: search.correlationConfidence },
                { key: 'groupBy', label: 'Group', value: search.groupBy },
                { key: 'constraintId', label: 'Constraint', value: search.constraintId },
                { key: 'invariantId', label: 'Invariant', value: search.invariantId },
              ]}
            />

            {activeGroups.length > 0 ? (
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                {activeGroups.map((group) => (
                  <Chip
                    key={`${group.key ?? 'empty'}-${group.count}`}
                    label={`${group.key ?? 'empty'} (${group.count})`}
                    onClick={() => applyGroupFilter(group.key)}
                    size="small"
                  />
                ))}
              </Stack>
            ) : null}

            {tab === 'explorer' ? (
              <QueryState
                empty={explorerRows.length === 0}
                error={explorerQuery.error}
                isError={explorerQuery.isError}
                isLoading={explorerQuery.isLoading}
                onRetry={() => void explorerQuery.refetch()}
              >
                <ServerDataGridPanel
                  ariaLabel="constraint explorer entries"
                  columns={explorerColumns}
                  getRowId={(row) => row.constraint_id}
                  loading={explorerQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onRowClick={(params) => replaceSearchParams({ constraintId: params.row.constraint_id })}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={explorerQuery.data?.pagination.total ?? 0}
                  rows={explorerRows}
                  sortModel={gridState.sortModel}
                />
              </QueryState>
            ) : tab === 'invariants' ? (
              <QueryState
                empty={invariantRowsNew.length === 0}
                error={invariantExplorerQuery.error}
                isError={invariantExplorerQuery.isError}
                isLoading={invariantExplorerQuery.isLoading}
                onRetry={() => void invariantExplorerQuery.refetch()}
              >
                <ServerDataGridPanel
                  ariaLabel="invariant explorer entries"
                  columns={invariantColumns}
                  getRowId={(row) => row.invariant_id}
                  loading={invariantExplorerQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onRowClick={(params) => replaceSearchParams({ invariantId: params.row.invariant_id })}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={invariantExplorerQuery.data?.pagination.total ?? 0}
                  rows={invariantRowsNew}
                  sortModel={gridState.sortModel}
                />
              </QueryState>
            ) : (
              <QueryState
                empty={legacyConstraintRows.length === 0}
                error={legacyQuery.error}
                isError={legacyQuery.isError}
                isLoading={legacyQuery.isLoading}
                onRetry={() => void legacyQuery.refetch()}
              >
                <ServerDataGridPanel
                  ariaLabel={`${tab} constraint entries`}
                  columns={legacyConstraintColumns}
                  getRowId={(row) => row.id}
                  loading={legacyQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={legacyQuery.data?.pagination.total ?? 0}
                  rows={legacyConstraintRows}
                  sortModel={gridState.sortModel}
                />
              </QueryState>
            )}
          </Stack>
        </CardContent>
      </Card>

      <InvestigationDrawer
        ariaLabel="Constraint detail"
        error={constraintDetailQuery.error}
        isError={constraintDetailQuery.isError}
        isLoading={constraintDetailQuery.isLoading}
        onClose={() => replaceSearchParams({ constraintId: undefined })}
        onRetry={() => void constraintDetailQuery.refetch()}
        open={constraintDetailOpen}
        subtitle={search.constraintId}
        title="Constraint detail"
      >
        {constraintDetailQuery.data ? (
          <Stack spacing={2}>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip label={constraintDetailQuery.data.source} size="small" />
              <Chip label={constraintDetailQuery.data.constraint_kind} size="small" variant="outlined" />
              <Chip label={constraintDetailQuery.data.agreement_status} size="small" variant="outlined" />
              <Chip label={constraintDetailQuery.data.assertion_available ? 'Assertion available' : 'No assertion'} size="small" />
            </Stack>
            <EvidenceLinkSet links={evidenceLinks} />
            <Typography component="h3" variant="subtitle2">
              Expression comparison
            </Typography>
            <JsonBlock maxHeight={240} value={{
              combined_expression: constraintDetailQuery.data.combined_expression,
              dynamic_expression: constraintDetailQuery.data.dynamic_expression,
              expression: constraintDetailQuery.data.expression,
              static_expression: constraintDetailQuery.data.static_expression,
            }} />
            <Typography component="h3" variant="subtitle2">
              Assertion
            </Typography>
            <JsonBlock maxHeight={160} value={constraintDetailQuery.data.assertion ?? constraintDetailQuery.data.assertion_preview} />
          </Stack>
        ) : null}
      </InvestigationDrawer>

      <InvestigationDrawer
        ariaLabel="Invariant detail"
        error={invariantDetailQuery.error}
        isError={invariantDetailQuery.isError}
        isLoading={invariantDetailQuery.isLoading}
        onClose={() => replaceSearchParams({ invariantId: undefined })}
        onRetry={() => void invariantDetailQuery.refetch()}
        open={invariantDetailOpen}
        subtitle={search.invariantId}
        title="Invariant detail"
      >
        {invariantDetailQuery.data ? (
          <Stack spacing={2}>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip label={invariantDetailQuery.data.invariant_kind} size="small" />
              <Chip label={invariantDetailQuery.data.oracle_readiness} size="small" variant="outlined" />
              <Chip label={invariantDetailQuery.data.correlation_confidence} size="small" variant="outlined" />
              <Chip label={invariantDetailQuery.data.assertion_available ? 'Assertion available' : 'No assertion'} size="small" />
            </Stack>
            <EvidenceLinkSet links={evidenceLinks} />
            <JsonBlock maxHeight={360} value={invariantDetailQuery.data} />
          </Stack>
        ) : null}
      </InvestigationDrawer>

      <InvestigationDrawer
        ariaLabel="Constraint detail"
        onClose={() => setLegacyDetail(null)}
        open={Boolean(legacyDetail)}
        subtitle="Legacy static/dynamic entry"
        title="Constraint detail"
      >
        <JsonBlock value={legacyDetail} />
      </InvestigationDrawer>

      <OperationDetailDrawer operationId={search.operationId} runName={runName} />

      <ExportSnapshotDialog
        data={activeRows}
        filters={search}
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={`/runs/${encodedRunName}/constraints`}
        selectedContext={constraintDetailQuery.data ?? invariantDetailQuery.data ?? legacyDetail}
        title="Constraints"
      />
    </Stack>
  )
}
