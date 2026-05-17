import DownloadIcon from '@mui/icons-material/Download'
import {
  Button,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  TextField,
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
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FacetFilterBar, type FacetFilter } from '../../shared/ui/FacetFilterBar'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
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
import { ConstraintDetailComposer } from './components/ConstraintDetailComposer'
import { ConstraintModeSegments } from './components/ConstraintModeSegments'
import { ConstraintWorkbench } from './components/ConstraintWorkbench'
import { CurrentPageConstraintMatrix } from './components/CurrentPageConstraintMatrix'
import { InvariantDetailComposer } from './components/InvariantDetailComposer'
import { LegacyConstraintDetailComposer } from './components/LegacyConstraintDetailComposer'
import type { MatrixBy } from './constraintViewModels'

export type ConstraintTab = 'dynamic' | 'explorer' | 'invariants' | 'static'

export type ConstraintsPageSearch = {
  agreementStatus?: string
  assertionAvailable?: boolean
  constraintDetailView?: 'raw' | 'readable'
  constraintId?: string
  constraintKind?: string
  constraintTab: ConstraintTab
  constraintsView?: 'matrix' | 'table' | 'workbench'
  correlationConfidence?: string
  groupBy?: string
  invariantId?: string
  invariantKind?: string
  invariantType?: string
  limit: number
  matrixBy?: MatrixBy
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
  const constraintsView = search.constraintsView ?? 'workbench'
  const constraintDetailView = search.constraintDetailView ?? 'readable'
  const matrixBy = search.matrixBy ?? 'source'
  const needsExplorer = constraintsView === 'workbench' || constraintsView === 'matrix' || (constraintsView === 'table' && tab === 'explorer')
  const needsInvariants = constraintsView === 'workbench' || constraintsView === 'matrix' || (constraintsView === 'table' && tab === 'invariants')
  const needsStatic = constraintsView === 'table' && tab === 'static'
  const needsDynamic = constraintsView === 'table' && tab === 'dynamic'
  const staticSummaryQuery = useStaticConstraintsSummary(runName)
  const dynamicSummaryQuery = useDynamicConstraintsSummary(runName)
  const explorerParams = toConstraintExplorerParams(search)
  const explorerFacetParams = toConstraintFacetParams(search)
  const invariantParams = toInvariantExplorerParams(search)
  const invariantFacetParams = toInvariantFacetParams(search)

  const explorerQuery = useConstraintExplorerEntries(runName, explorerParams, { query: { enabled: needsExplorer } })
  const explorerFacetsQuery = useConstraintExplorerFacets(runName, explorerFacetParams, { query: { enabled: needsExplorer } })
  const constraintDetailOpen = Boolean(search.constraintId)
  const constraintDetailQuery = useConstraintExplorerDetail(
    runName,
    search.constraintId ?? '',
    { query: { enabled: constraintDetailOpen } },
  )
  const invariantExplorerQuery = useInvariantExplorerEntries(runName, invariantParams, { query: { enabled: needsInvariants } })
  const invariantFacetsQuery = useInvariantExplorerFacets(runName, invariantFacetParams, { query: { enabled: needsInvariants } })
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
  }, { query: { enabled: needsStatic } })
  const dynamicEntriesQuery = useDynamicConstraintEntries(runName, {
    group_by: search.groupBy,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    q: search.q,
    section: search.section,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
  }, { query: { enabled: needsDynamic } })

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

  function applyMatrixFilter(filter: Record<string, string | undefined>) {
    replaceSearchParams({
      ...filter,
      constraintTab: filter.oracleReadiness ? 'invariants' : 'explorer',
      constraintsView: 'table',
      offset: 0,
    })
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
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
            <ConstraintModeSegments constraintTab={tab} constraintsView={constraintsView} />
            <Button onClick={() => setExportOpen(true)} startIcon={<DownloadIcon />} variant="outlined">
              Export snapshot
            </Button>
          </Stack>
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

            {constraintsView === 'workbench' ? (
              <QueryState
                empty={explorerRows.length === 0 && invariantRowsNew.length === 0}
                error={explorerQuery.error ?? invariantExplorerQuery.error}
                isError={explorerQuery.isError || invariantExplorerQuery.isError}
                isLoading={explorerQuery.isLoading || invariantExplorerQuery.isLoading}
                onRetry={() => {
                  void explorerQuery.refetch()
                  void invariantExplorerQuery.refetch()
                }}
              >
                <ConstraintWorkbench
                  constraints={explorerRows}
                  invariants={invariantRowsNew}
                  matrixBy={matrixBy}
                  onApplyFilter={applyMatrixFilter}
                  onMatrixByChange={(value) => replaceSearchParams({ matrixBy: value })}
                  onSelectConstraint={(constraintId) => replaceSearchParams({ constraintId })}
                  onSelectInvariant={(invariantId) => replaceSearchParams({ invariantId })}
                />
              </QueryState>
            ) : constraintsView === 'matrix' ? (
              <QueryState
                empty={explorerRows.length === 0 && invariantRowsNew.length === 0}
                error={explorerQuery.error ?? invariantExplorerQuery.error}
                isError={explorerQuery.isError || invariantExplorerQuery.isError}
                isLoading={explorerQuery.isLoading || invariantExplorerQuery.isLoading}
                onRetry={() => {
                  void explorerQuery.refetch()
                  void invariantExplorerQuery.refetch()
                }}
              >
                <CurrentPageConstraintMatrix
                  constraints={explorerRows}
                  invariants={invariantRowsNew}
                  matrixBy={matrixBy}
                  onApplyFilter={applyMatrixFilter}
                />
              </QueryState>
            ) : tab === 'explorer' ? (
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
          <ConstraintDetailComposer
            detail={constraintDetailQuery.data}
            detailView={constraintDetailView}
            evidenceLinks={evidenceLinks}
            onDetailViewChange={(value) => replaceSearchParams({ constraintDetailView: value })}
          />
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
          <InvariantDetailComposer
            detail={invariantDetailQuery.data}
            detailView={constraintDetailView}
            evidenceLinks={evidenceLinks}
            onDetailViewChange={(value) => replaceSearchParams({ constraintDetailView: value })}
          />
        ) : null}
      </InvestigationDrawer>

      <InvestigationDrawer
        ariaLabel="Constraint detail"
        onClose={() => setLegacyDetail(null)}
        open={Boolean(legacyDetail)}
        subtitle="Legacy static/dynamic entry"
        title="Constraint detail"
      >
        {legacyDetail ? <LegacyConstraintDetailComposer detail={legacyDetail} /> : null}
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
