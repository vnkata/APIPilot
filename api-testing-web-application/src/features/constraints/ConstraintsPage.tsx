import {
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import type { GridColDef, GridRowSelectionModel } from '@mui/x-data-grid'
import { useCallback, useMemo, useState } from 'react'

import type {
  CombinationReviewFinalizeRequest,
  CounterExampleGenerateRequest,
  CounterExampleRunRequest,
  CombinationEntryResponse,
  ConstraintEntryDetailResponse,
  ConstraintExplorerEntryResponse,
  JsonValue,
  InvariantExplorerEntryResponse,
  SortOrder,
} from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { PageLearningPanel } from '../../shared/ui/Guidance'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
import {
  toCombinationFacetParams,
  toCombinationParams,
  toConstraintExplorerParams,
  toConstraintFacetParams,
  toInvariantExplorerParams,
  toInvariantFacetParams,
  useCombinationDetail,
  useCombinationEntries,
  useCombinationFacets,
  useCombinationReview,
  useCombinationSummary,
  useBatchGenerateCounterExamples,
  useConstraintExplorerDetail,
  useConstraintExplorerEntries,
  useConstraintExplorerFacets,
  useDynamicConstraintEntries,
  useDynamicConstraintsSummary,
  useFinalizeCombinationReview,
  useGenerateCounterExamples,
  useInvariantExplorerDetail,
  useInvariantExplorerEntries,
  useInvariantExplorerFacets,
  useReopenCombinationReview,
  useRunCounterExamples,
  useStaticConstraintEntries,
  useStaticConstraintsSummary,
  useUpdateCounterExampleCase,
} from './api'
import { ConstraintAdvancedFiltersDrawer } from './components/ConstraintAdvancedFiltersDrawer'
import { ConstraintAppliedFiltersBar } from './components/ConstraintAppliedFiltersBar'
import { CombinationDetailComposer } from './components/CombinationDetailComposer'
import { ConstraintDetailComposer } from './components/ConstraintDetailComposer'
import { ConstraintFilterPanel } from './components/ConstraintFilterPanel'
import { ConstraintPageHeader } from './components/ConstraintPageHeader'
import { ConstraintResultsRegion } from './components/ConstraintResultsRegion'
import { InvariantDetailComposer } from './components/InvariantDetailComposer'
import { LegacyConstraintDetailComposer } from './components/LegacyConstraintDetailComposer'
import {
  deriveCombinationReviewSignal,
  isCombinationEligibleForCounterExample,
  type MatrixBy,
} from './constraintViewModels'
import type { ConstraintGridColumns, ConstraintQueryState, LegacyConstraintRow } from './types'
import {
  CombinationPriorityBadge,
  CombinationRelationBadge,
  CombinationStatusBadge,
  ReviewStateBadge,
  RuntimeVerdictBadge,
} from './components/CombinationBadges'

export type ConstraintTab = 'combination' | 'dynamic' | 'explorer' | 'invariants' | 'static'

export type ConstraintsPageSearch = {
  agreementStatus?: string
  assertionAvailable?: boolean
  combinationId?: string
  constraintDetailView?: 'raw' | 'readable'
  constraintId?: string
  constraintKind?: string
  constraintTab: ConstraintTab
  constraintsView?: 'matrix' | 'table' | 'workbench'
  correlationConfidence?: string
  decisionSource?: string
  groupBy?: string
  hasCounterExample?: boolean
  hasManualDecision?: boolean
  hasRuntimeEvaluation?: boolean
  hasValidationCases?: boolean
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
  relation?: string
  reviewState?: string
  resolved?: boolean
  section?: string
  sortBy?: string
  sortOrder?: SortOrder
  source?: string
  sourceType?: string
  status?: string
  runtimeVerdict?: string
}

type ConstraintsPageProps = {
  runName: string
  search: ConstraintsPageSearch
}

function constraintRows(items: ConstraintEntryDetailResponse[]) {
  return items.map((item, index) => ({
    ...item,
    id: `${item.operation_id}:${item.section ?? 'dynamic'}:${item.property_path}:${index}`,
  }))
}

export function ConstraintsPage({ runName, search }: ConstraintsPageProps) {
  const [legacyDetail, setLegacyDetail] = useState<LegacyConstraintRow | null>(null)
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false)
  const [batchConfirmOpen, setBatchConfirmOpen] = useState(false)
  const [batchGenerateMessage, setBatchGenerateMessage] = useState<string | null>(null)
  const [batchGenerateLiveLlm, setBatchGenerateLiveLlm] = useState(true)
  const [combinationSelectionModel, setCombinationSelectionModel] = useState<GridRowSelectionModel>({ ids: new Set(), type: 'include' })
  const [exportOpen, setExportOpen] = useState(false)
  const encodedRunName = encodeRoutePart(runName)
  const gridState = useUrlBackedGridState(search)
  const tab = search.constraintTab ?? 'explorer'
  const constraintsView = search.constraintsView ?? 'workbench'
  const constraintDetailView = search.constraintDetailView ?? 'readable'
  const matrixBy = search.matrixBy ?? 'source'
  const needsCombination = constraintsView === 'workbench' || (constraintsView === 'table' && tab === 'combination')
  const needsExplorer = constraintsView === 'workbench' || constraintsView === 'matrix' || (constraintsView === 'table' && tab === 'explorer')
  const needsInvariants = constraintsView === 'workbench' || constraintsView === 'matrix' || (constraintsView === 'table' && tab === 'invariants')
  const needsStatic = constraintsView === 'table' && tab === 'static'
  const needsDynamic = constraintsView === 'table' && tab === 'dynamic'
  const staticSummaryQuery = useStaticConstraintsSummary(runName)
  const dynamicSummaryQuery = useDynamicConstraintsSummary(runName)
  const explorerParams = toConstraintExplorerParams(search)
  const explorerFacetParams = toConstraintFacetParams(search)
  const combinationParams = toCombinationParams(search)
  const combinationFacetParams = toCombinationFacetParams(search)
  const invariantParams = toInvariantExplorerParams(search)
  const invariantFacetParams = toInvariantFacetParams(search)

  const combinationSummaryQuery = useCombinationSummary(runName)
  const combinationQuery = useCombinationEntries(runName, combinationParams, { query: { enabled: needsCombination } })
  const combinationFacetsQuery = useCombinationFacets(runName, combinationFacetParams, { query: { enabled: needsCombination } })
  const combinationDetailOpen = Boolean(search.combinationId)
  const combinationDetailQuery = useCombinationDetail(
    runName,
    search.combinationId ?? '',
    { query: { enabled: combinationDetailOpen } },
  )
  const combinationReviewQuery = useCombinationReview(
    runName,
    search.combinationId ?? '',
    { query: { enabled: combinationDetailOpen } },
  )
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

  function refetchCombinationReviewSurface() {
    void combinationQuery.refetch()
    void combinationFacetsQuery.refetch()
    void combinationDetailQuery.refetch()
    void combinationReviewQuery.refetch()
    void explorerQuery.refetch()
    void explorerFacetsQuery.refetch()
  }

  const generateCounterExamplesMutation = useGenerateCounterExamples({
    mutation: {
      onSuccess: refetchCombinationReviewSurface,
    },
  })
  const updateCounterExampleCaseMutation = useUpdateCounterExampleCase({
    mutation: {
      onSuccess: refetchCombinationReviewSurface,
    },
  })
  const runCounterExamplesMutation = useRunCounterExamples({
    mutation: {
      onSuccess: refetchCombinationReviewSurface,
    },
  })
  const finalizeReviewMutation = useFinalizeCombinationReview({
    mutation: {
      onSuccess: refetchCombinationReviewSurface,
    },
  })
  const reopenReviewMutation = useReopenCombinationReview({
    mutation: {
      onSuccess: refetchCombinationReviewSurface,
    },
  })
  const batchGenerateCounterExamplesMutation = useBatchGenerateCounterExamples({
    mutation: {
      onSuccess: (response) => {
        const generated = response.results.filter((item) => item.status === 'generated').length
        const newCaseCount = response.results.reduce((total, item) => total + (item.new_case_count ?? item.case_count), 0)
        const totalCaseCount = response.results.reduce((total, item) => total + (item.total_case_count ?? item.case_count), 0)
        setBatchGenerateMessage(
          `Generated ${newCaseCount} new draft${newCaseCount === 1 ? '' : 's'} for ${generated} row${generated === 1 ? '' : 's'} (${totalCaseCount} total).`,
        )
        void combinationQuery.refetch()
        void combinationFacetsQuery.refetch()
        void explorerQuery.refetch()
        void explorerFacetsQuery.refetch()
      },
    },
  })

  const legacyConstraintRows = useMemo(
    () => constraintRows((tab === 'dynamic' ? dynamicEntriesQuery.data?.items : staticEntriesQuery.data?.items) ?? []),
    [dynamicEntriesQuery.data?.items, staticEntriesQuery.data?.items, tab],
  )
  const combinationRows = useMemo(() => combinationQuery.data?.items ?? [], [combinationQuery.data?.items])
  const selectedCombinationRows = useMemo(() => {
    if (combinationSelectionModel.type === 'exclude') {
      return combinationRows.filter((row) => !combinationSelectionModel.ids.has(row.combination_id))
    }
    return combinationRows.filter((row) => combinationSelectionModel.ids.has(row.combination_id))
  }, [combinationRows, combinationSelectionModel])
  const selectedEligibleCombinationRows = useMemo(
    () => selectedCombinationRows.filter((row) => isCombinationEligibleForCounterExample(row)),
    [selectedCombinationRows],
  )
  const selectedCombinationCount = selectedCombinationRows.length
  const selectedEligibleCombinationCount = selectedEligibleCombinationRows.length
  const selectedSkippedCombinationCount = Math.max(0, selectedCombinationCount - selectedEligibleCombinationCount)
  const isCombinationSelected = useCallback((combinationId: string) => {
    if (combinationSelectionModel.type === 'exclude') return !combinationSelectionModel.ids.has(combinationId)
    return combinationSelectionModel.ids.has(combinationId)
  }, [combinationSelectionModel])

  const toggleCombinationSelection = useCallback((combinationId: string, checked: boolean) => {
    setCombinationSelectionModel((current) => {
      const nextIds = new Set(current.ids)
      if (current.type === 'exclude') {
        if (checked) nextIds.delete(combinationId)
        else nextIds.add(combinationId)
        return { ids: nextIds, type: 'exclude' }
      }
      if (checked) nextIds.add(combinationId)
      else nextIds.delete(combinationId)
      return { ids: nextIds, type: 'include' }
    })
    setBatchGenerateMessage(null)
  }, [])

  const explorerRows = explorerQuery.data?.items ?? []
  const invariantRowsNew = invariantExplorerQuery.data?.items ?? []
  const legacyQuery = tab === 'dynamic' ? dynamicEntriesQuery : staticEntriesQuery
  const activeGroups =
    tab === 'combination'
      ? combinationQuery.data?.groups ?? []
      : tab === 'explorer'
      ? explorerQuery.data?.groups ?? []
      : tab === 'invariants'
        ? invariantExplorerQuery.data?.groups ?? []
        : legacyQuery.data?.groups ?? []
  const activeRows =
    tab === 'combination'
      ? combinationRows
      : tab === 'explorer'
      ? explorerRows
      : tab === 'invariants'
        ? invariantRowsNew
        : legacyConstraintRows

  const combinationColumns = useMemo<GridColDef<CombinationEntryResponse>[]>(
    () => [
      {
        field: 'select_for_batch',
        headerName: '',
        minWidth: 64,
        sortable: false,
        renderCell: (params) => {
          const eligible = isCombinationEligibleForCounterExample(params.row)
          return (
            <Tooltip
              arrow
              title={eligible ? 'Select this row for draft generation.' : 'This row can be selected for review context, but batch generation will skip it because it is resolved, unique, or manually decided.'}
            >
              <span>
                <Checkbox
                  checked={isCombinationSelected(params.row.combination_id)}
                  onChange={(event) => toggleCombinationSelection(params.row.combination_id, event.target.checked)}
                  onClick={(event) => event.stopPropagation()}
                  size="small"
                  slotProps={{ input: { 'aria-label': `Select ${params.row.combination_id} for batch generation` } }}
                />
              </span>
            </Tooltip>
          )
        },
      },
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
      {
        field: 'review_priority',
        headerName: 'Review priority',
        minWidth: 210,
        sortable: false,
        renderCell: (params) => <CombinationPriorityBadge row={params.row} />,
        valueGetter: (_value, row) => deriveCombinationReviewSignal(row).label,
      },
      {
        field: 'relation_badge',
        headerName: 'Relation',
        minWidth: 190,
        renderCell: (params) => <CombinationRelationBadge relation={params.row.relation} />,
        valueGetter: (_value, row) => row.relation,
      },
      {
        field: 'status_badge',
        headerName: 'Status',
        minWidth: 170,
        renderCell: (params) => <CombinationStatusBadge status={params.row.status} />,
        valueGetter: (_value, row) => row.status,
      },
      {
        field: 'runtime_verdict_badge',
        headerName: 'Runtime support',
        minWidth: 190,
        renderCell: (params) => <RuntimeVerdictBadge runtimeVerdict={params.row.runtime_verdict} />,
        valueGetter: (_value, row) => row.runtime_verdict,
      },
      {
        field: 'review_state',
        headerName: 'Review',
        minWidth: 190,
        renderCell: (params) => <ReviewStateBadge row={params.row} />,
      },
      {
        field: 'resolved',
        headerName: 'Resolved',
        minWidth: 120,
        renderCell: (params) => (params.row.resolved ? 'Resolved' : 'Unresolved'),
      },
      { field: 'property_path', flex: 1, headerName: 'Property path', minWidth: 180 },
      {
        field: 'final_constraint',
        flex: 1.5,
        headerName: 'Final constraint',
        minWidth: 280,
        renderCell: (params) => (
          <Button color="inherit" onClick={() => replaceSearchParams({ combinationId: params.row.combination_id })} size="small">
            {params.row.final_constraint ?? params.row.static_constraint ?? params.row.dynamic_constraint ?? params.row.combination_id}
          </Button>
        ),
      },
      { field: 'validation_case_count', headerName: 'Cases', minWidth: 100 },
    ],
    [isCombinationSelected, toggleCombinationSelection],
  )
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
      {
        field: 'manual_decision',
        headerName: 'Review',
        minWidth: 180,
        renderCell: (params) => (
          <Stack spacing={0.5}>
            <ReviewStateBadge
              row={{
                decision_source: params.row.decision_source,
                has_manual_decision: params.row.has_manual_decision,
                manual_decision: params.row.manual_decision,
                review_state: params.row.review_state,
              }}
            />
            {params.row.manual_final_constraint ? (
              <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="caption">
                Effective final: {params.row.manual_final_constraint}
              </Typography>
            ) : params.row.has_manual_decision && ['NO_FINAL', 'NEEDS_BUSINESS_REVIEW', 'REJECT_RELATION'].includes(params.row.manual_decision ?? '') ? (
              <Typography color="text.secondary" variant="caption">
                No effective final
              </Typography>
            ) : params.row.has_manual_decision ? (
              <Typography color="text.secondary" variant="caption">
                Effective final decided by reviewer
              </Typography>
            ) : null}
          </Stack>
        ),
      },
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
  const columns = useMemo<ConstraintGridColumns>(
    () => ({
      combination: combinationColumns,
      explorer: explorerColumns,
      invariants: invariantColumns,
      legacy: legacyConstraintColumns,
    }),
    [combinationColumns, explorerColumns, invariantColumns, legacyConstraintColumns],
  )

  function handleBatchGenerateCounterExamples() {
    if (selectedEligibleCombinationRows.length === 0) return
    setBatchConfirmOpen(true)
  }

  function handleConfirmBatchGenerateCounterExamples() {
    const combinationIds = selectedEligibleCombinationRows.map((row) => row.combination_id)
    if (combinationIds.length === 0) return
    batchGenerateCounterExamplesMutation.mutate({
      runName,
      data: {
        combination_ids: combinationIds,
        idempotency_key: createIdempotencyKey('batch-generate'),
        live_llm: batchGenerateLiveLlm,
        max_cases_per_item: 3,
        max_items: combinationIds.length,
      },
    })
    setBatchConfirmOpen(false)
  }

  function handleGenerateCounterExamples(data: CounterExampleGenerateRequest) {
    if (!search.combinationId) return
    generateCounterExamplesMutation.mutate({ runName, combinationId: search.combinationId, data })
  }

  function handleUpdateCounterExampleCase(
    caseId: string,
    caseState: string,
    rationale: string,
    request?: JsonValue | null,
  ) {
    if (!search.combinationId) return
    updateCounterExampleCaseMutation.mutate({
      runName,
      combinationId: search.combinationId,
      caseId,
      data: { case_state: caseState, rationale, request },
    })
  }

  function handleRunApprovedCounterExamples(data: CounterExampleRunRequest) {
    if (!search.combinationId) return
    runCounterExamplesMutation.mutate({ runName, combinationId: search.combinationId, data })
  }

  function handleFinalizeReview(data: CombinationReviewFinalizeRequest) {
    if (!search.combinationId) return
    finalizeReviewMutation.mutate({ runName, combinationId: search.combinationId, data })
  }

  function handleReopenReview(rationale: string) {
    if (!search.combinationId) return
    reopenReviewMutation.mutate({ runName, combinationId: search.combinationId, data: { rationale } })
  }

  function applyGroupFilter(key: string | null | undefined) {
    if (!key) return
    if (search.groupBy === 'operation_id') replaceSearchParams({ offset: 0, operationId: key })
    if (search.groupBy === 'section') replaceSearchParams({ offset: 0, section: key })
    if (search.groupBy === 'source') replaceSearchParams({ offset: 0, source: key })
    if (search.groupBy === 'constraint_kind') replaceSearchParams({ constraintKind: key, offset: 0 })
    if (search.groupBy === 'agreement_status') replaceSearchParams({ agreementStatus: key, offset: 0 })
    if (search.groupBy === 'status') replaceSearchParams({ offset: 0, status: key })
    if (search.groupBy === 'relation') replaceSearchParams({ offset: 0, relation: key })
    if (search.groupBy === 'runtime_verdict') replaceSearchParams({ offset: 0, runtimeVerdict: key })
    if (search.groupBy === 'resolved') replaceSearchParams({ offset: 0, resolved: key })
    if (search.groupBy === 'has_counter_example') replaceSearchParams({ hasCounterExample: key, offset: 0 })
    if (search.groupBy === 'has_runtime_evaluation') replaceSearchParams({ hasRuntimeEvaluation: key, offset: 0 })
    if (search.groupBy === 'has_validation_cases') replaceSearchParams({ hasValidationCases: key, offset: 0 })
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

  const selectedOperationId =
    combinationDetailQuery.data?.operation_id ??
    constraintDetailQuery.data?.operation_id ??
    invariantDetailQuery.data?.operation_id ??
    search.operationId
  const encodedOperationId = encodeURIComponent(selectedOperationId ?? '')
  const evidenceLinks = selectedOperationId
    ? [
        { href: `/runs/${encodedRunName}/graph?operationId=${encodedOperationId}`, label: 'Graph' },
        { href: `/runs/${encodedRunName}/test-cases?operationId=${encodedOperationId}`, label: 'Test cases' },
        { href: `/runs/${encodedRunName}/reports?operationId=${encodedOperationId}`, label: 'Reports' },
      ]
    : []
  const combinationState: ConstraintQueryState = {
    error: combinationQuery.error,
    isError: combinationQuery.isError,
    isFetching: combinationQuery.isFetching,
    isLoading: combinationQuery.isLoading,
    refetch: combinationQuery.refetch,
  }
  const explorerState: ConstraintQueryState = {
    error: explorerQuery.error,
    isError: explorerQuery.isError,
    isFetching: explorerQuery.isFetching,
    isLoading: explorerQuery.isLoading,
    refetch: explorerQuery.refetch,
  }
  const invariantState: ConstraintQueryState = {
    error: invariantExplorerQuery.error,
    isError: invariantExplorerQuery.isError,
    isFetching: invariantExplorerQuery.isFetching,
    isLoading: invariantExplorerQuery.isLoading,
    refetch: invariantExplorerQuery.refetch,
  }
  const legacyState: ConstraintQueryState = {
    error: legacyQuery.error,
    isError: legacyQuery.isError,
    isFetching: legacyQuery.isFetching,
    isLoading: legacyQuery.isLoading,
    refetch: legacyQuery.refetch,
  }

  return (
    <Stack spacing={2}>
      <ConstraintPageHeader
        combinationCount={
          combinationSummaryQuery.data
            ? combinationSummaryQuery.data.resolved_count + combinationSummaryQuery.data.unresolved_count
            : combinationQuery.data?.pagination.total ?? 0
        }
        constraintTab={tab}
        constraintsView={constraintsView}
        dynamicCount={dynamicSummaryQuery.data?.constraint_count ?? 0}
        invariantCount={dynamicSummaryQuery.data?.invariant_count ?? invariantExplorerQuery.data?.pagination.total ?? 0}
        onExport={() => setExportOpen(true)}
        staticCount={staticSummaryQuery.data?.constraint_count ?? 0}
      />

      <PageLearningPanel
        defaultExpanded
        sections={[
          {
            body: 'Source tells you whether the signal came from static mining, dynamic observations, or a combined static/dynamic view.',
            title: 'Start with source',
          },
          {
            body: 'Agreement explains whether static and runtime evidence support each other, conflict, or only exist on one side.',
            title: 'Then check agreement',
          },
          {
            body: 'Assertion availability and oracle readiness tell you whether a signal can become executable test logic or still needs human review.',
            title: 'Decide the next action',
          },
        ]}
        {...tourAnchor(TOUR_ANCHORS.constraintsLearningPanel)}
      />

      <ConstraintFilterPanel
        combinationFacets={combinationFacetsQuery.data}
        constraintFacets={explorerFacetsQuery.data}
        invariantFacets={invariantFacetsQuery.data}
        onAdvancedOpen={() => setAdvancedFiltersOpen(true)}
        search={search}
        tab={tab}
      />

      <ConstraintAppliedFiltersBar search={search} />

      <ConstraintResultsRegion
        columns={columns}
        combinationQuery={combinationState}
        batchGenerateMessage={batchGenerateMessage}
        batchGeneratePending={batchGenerateCounterExamplesMutation.isPending}
        combinationRowCount={combinationQuery.data?.pagination.total ?? 0}
        combinationRows={combinationRows}
        constraintsView={constraintsView}
        explorerQuery={explorerState}
        explorerRowCount={explorerQuery.data?.pagination.total ?? 0}
        explorerRows={explorerRows}
        gridState={gridState}
        invariantQuery={invariantState}
        invariantRowCount={invariantExplorerQuery.data?.pagination.total ?? 0}
        invariantRows={invariantRowsNew}
        legacyQuery={legacyState}
        legacyRowCount={legacyQuery.data?.pagination.total ?? 0}
        legacyRows={legacyConstraintRows}
        matrixBy={matrixBy}
        onApplyMatrixFilter={applyMatrixFilter}
        onBatchGenerateCounterExamples={handleBatchGenerateCounterExamples}
        onMatrixByChange={(value) => replaceSearchParams({ matrixBy: value })}
        onSelectCombination={(combinationId) => replaceSearchParams({ combinationId })}
        onSelectConstraint={(constraintId) => replaceSearchParams({ constraintId })}
        onSelectInvariant={(invariantId) => replaceSearchParams({ invariantId })}
        selectedEligibleCombinationCount={selectedEligibleCombinationCount}
        selectedSkippedCombinationCount={selectedSkippedCombinationCount}
        selectedCombinationCount={selectedCombinationCount}
        tab={tab}
      />

      <ConstraintAdvancedFiltersDrawer
        activeGroups={activeGroups}
        combinationFacets={combinationFacetsQuery.data}
        constraintFacets={explorerFacetsQuery.data}
        invariantFacets={invariantFacetsQuery.data}
        onApplyGroupFilter={applyGroupFilter}
        onClose={() => setAdvancedFiltersOpen(false)}
        open={advancedFiltersOpen}
        search={search}
        tab={tab}
      />

      <InvestigationDrawer
        ariaLabel="Combination detail"
        error={combinationDetailQuery.error}
        isError={combinationDetailQuery.isError}
        isLoading={combinationDetailQuery.isLoading}
        onClose={() => replaceSearchParams({ combinationId: undefined })}
        onRetry={() => void combinationDetailQuery.refetch()}
        open={combinationDetailOpen}
        subtitle={search.combinationId}
        title="Combination detail"
        data-tour-anchor={TOUR_ANCHORS.constraintsDetail}
      >
        {combinationDetailQuery.data ? (
          <CombinationDetailComposer
            detail={combinationDetailQuery.data}
            detailView={constraintDetailView}
            evidenceLinks={evidenceLinks}
            mode="preview"
            onApproveCase={(caseId, request) => handleUpdateCounterExampleCase(caseId, 'APPROVED', 'Approved for targeted HITL execution.', request)}
            onDetailViewChange={(value) => replaceSearchParams({ constraintDetailView: value })}
            onFinalize={handleFinalizeReview}
            onGenerateDraft={handleGenerateCounterExamples}
            onRejectCase={(caseId) => handleUpdateCounterExampleCase(caseId, 'REJECTED', 'Rejected during HITL review.')}
            onReopen={handleReopenReview}
            onRunApproved={handleRunApprovedCounterExamples}
            review={combinationReviewQuery.data}
            reviewHref={`/runs/${encodedRunName}/constraints/combination/${encodeURIComponent(combinationDetailQuery.data.combination_id)}/review`}
            reviewActionError={
              generateCounterExamplesMutation.error ||
              updateCounterExampleCaseMutation.error ||
              runCounterExamplesMutation.error ||
              finalizeReviewMutation.error ||
              reopenReviewMutation.error
            }
            reviewActionPending={
              generateCounterExamplesMutation.isPending ||
              updateCounterExampleCaseMutation.isPending ||
              runCounterExamplesMutation.isPending ||
              finalizeReviewMutation.isPending ||
              reopenReviewMutation.isPending
            }
            reviewLoading={combinationReviewQuery.isLoading}
          />
        ) : null}
      </InvestigationDrawer>

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
        data-tour-anchor={TOUR_ANCHORS.constraintsDetail}
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
        data-tour-anchor={TOUR_ANCHORS.constraintsDetail}
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
        data-tour-anchor={TOUR_ANCHORS.constraintsDetail}
      >
        {legacyDetail ? <LegacyConstraintDetailComposer detail={legacyDetail} /> : null}
      </InvestigationDrawer>

      <OperationDetailDrawer operationId={search.operationId} runName={runName} />

      <Dialog
        aria-labelledby="batch-generate-confirm-title"
        onClose={() => setBatchConfirmOpen(false)}
        open={batchConfirmOpen}
      >
        <DialogTitle id="batch-generate-confirm-title">Confirm live draft generation</DialogTitle>
        <DialogContent>
          <Stack spacing={1}>
            <Typography variant="body2">
              {selectedCombinationCount} selected row{selectedCombinationCount === 1 ? '' : 's'}.
            </Typography>
            <Typography variant="body2">
              {selectedEligibleCombinationCount} eligible; {selectedSkippedCombinationCount} skipped.
            </Typography>
            {selectedSkippedCombinationCount > 0 ? (
              <Typography color="text.secondary" variant="body2">
                Skipped rows are resolved, unique, or manually decided and will not be sent to the backend batch request.
              </Typography>
            ) : null}
            <FormControlLabel
              control={<Checkbox checked={batchGenerateLiveLlm} onChange={(event) => setBatchGenerateLiveLlm(event.target.checked)} />}
              label="Use live LLM for selected rows"
            />
            <Typography color="text.secondary" variant="body2">
              Live LLM draft generation can add latency and provider cost. This action generates up to 3 cases per eligible row.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBatchConfirmOpen(false)}>Cancel</Button>
          <Button
            disabled={batchGenerateCounterExamplesMutation.isPending || selectedEligibleCombinationCount === 0}
            onClick={handleConfirmBatchGenerateCounterExamples}
            variant="contained"
          >
            Confirm live generation
          </Button>
        </DialogActions>
      </Dialog>

      <ExportSnapshotDialog
        data={activeRows}
        filters={search}
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={`/runs/${encodedRunName}/constraints`}
        selectedContext={combinationDetailQuery.data ?? constraintDetailQuery.data ?? invariantDetailQuery.data ?? legacyDetail}
        title="Constraints"
      />
    </Stack>
  )
}

function createIdempotencyKey(action: string) {
  const randomValue = globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2)
  return `${action}-${Date.now()}-${randomValue}`
}
