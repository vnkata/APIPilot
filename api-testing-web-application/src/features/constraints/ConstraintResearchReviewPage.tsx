import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
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
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import type { GridColDef, GridPaginationModel } from '@mui/x-data-grid'
import { useEffect, useMemo, useState } from 'react'

import type {
  ConstraintResearchDetailResponse,
  ConstraintResearchEntryResponse,
  ConstraintResearchEvidenceCaseResponse,
  ConstraintResearchSummaryResponse,
} from '../../shared/api/generated/model'
import { encodeRoutePart, formatDateTime } from '../../shared/lib/format'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import {
  toConstraintResearchParams,
  useConstraintResearchDetail,
  useConstraintResearchEntries,
  useConstraintResearchSummary,
  useUpdateConstraintResearchLabels,
} from './api'
import { CombinationRelationBadge, CombinationStatusBadge } from './components/CombinationBadges'

type ConstraintResearchReviewPageProps = {
  runName: string
}

type ResearchLabel = 'TP' | 'FP' | 'UNSURE'
type CombinedResearchLabel = ResearchLabel | ''
type LabelDraft = {
  combinedLabel: CombinedResearchLabel
  dynamicLabel: ResearchLabel
  notes: string
  staticLabel: ResearchLabel
}

const LABEL_OPTIONS: ResearchLabel[] = ['TP', 'FP', 'UNSURE']

export function ConstraintResearchReviewPage({ runName }: ConstraintResearchReviewPageProps) {
  const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 })
  const [relation, setRelation] = useState('')
  const [runtimeRecommendation, setRuntimeRecommendation] = useState('')
  const [invalidReason, setInvalidReason] = useState('')
  const [labelState, setLabelState] = useState('')
  const [orphanedFilter, setOrphanedFilter] = useState<'active' | 'orphaned' | 'all'>('active')
  const [selectedPairId, setSelectedPairId] = useState<string | null>(null)
  const [isDetailOpen, setIsDetailOpen] = useState(true)
  const [detailWidth, setDetailWidth] = useState(() => {
    const stored = Number(window.localStorage.getItem(`apipilot.constraintResearch.detailWidth.${runName}`))
    return Number.isFinite(stored) && stored >= 360 && stored <= 760 ? stored : 460
  })
  const [labelDrafts, setLabelDrafts] = useState<Record<string, LabelDraft>>({})
  const [savedLabelBaselines, setSavedLabelBaselines] = useState<Record<string, LabelDraft>>({})
  const [saveMessage, setSaveMessage] = useState<string | null>(null)
  const encodedRunName = encodeRoutePart(runName)

  const researchParams = toConstraintResearchParams({
    invalidReason: invalidReason || undefined,
    labelState: labelState || undefined,
    limit: paginationModel.pageSize,
    offset: paginationModel.page * paginationModel.pageSize,
    orphaned: orphanedFilter === 'all' ? null : orphanedFilter === 'orphaned',
    relation: relation || undefined,
    runtimeRecommendation: runtimeRecommendation || undefined,
  })
  const summaryQuery = useConstraintResearchSummary(runName)
  const entriesQuery = useConstraintResearchEntries(runName, researchParams)
  const rows = entriesQuery.data?.items ?? []
  const activePairId =
    selectedPairId && rows.some((row) => row.research_pair_id === selectedPairId || row.combination_id === selectedPairId)
      ? selectedPairId
      : rows[0]?.research_pair_id ?? null
  const activeRowIndex = activePairId
    ? rows.findIndex((row) => row.research_pair_id === activePairId || row.combination_id === activePairId)
    : -1
  const detailQuery = useConstraintResearchDetail(
    runName,
    activePairId ?? '',
    { query: { enabled: Boolean(activePairId) } },
  )
  const updateLabelsMutation = useUpdateConstraintResearchLabels({
    mutation: {
      onSuccess: (entry) => {
        setSavedLabelBaselines((current) => ({
          ...current,
          [entry.research_pair_id]: draftFromResearchEntry(entry),
        }))
        setLabelDrafts((current) => {
          const next = { ...current }
          delete next[entry.research_pair_id]
          return next
        })
        setSaveMessage(`Saved labels for ${entry.property_path}.`)
        void entriesQuery.refetch()
        void summaryQuery.refetch()
        void detailQuery.refetch()
      },
    },
  })
  const summary = summaryQuery.data
  const selectedDetail = detailQuery.data
  const baselineDraft = selectedDetail
    ? savedLabelBaselines[selectedDetail.research_pair_id] ?? draftFromResearchEntry(selectedDetail)
    : null
  const editedDraft = selectedDetail ? labelDrafts[selectedDetail.research_pair_id] : undefined
  const staticLabel = editedDraft?.staticLabel ?? baselineDraft?.staticLabel ?? 'UNSURE'
  const dynamicLabel = editedDraft?.dynamicLabel ?? baselineDraft?.dynamicLabel ?? 'UNSURE'
  const combinedLabel = editedDraft?.combinedLabel ?? baselineDraft?.combinedLabel ?? ''
  const notes = editedDraft?.notes ?? baselineDraft?.notes ?? ''
  const selectedCombinedLabel = combinedLabel || null
  const isDirty = baselineDraft
    ? staticLabel !== baselineDraft.staticLabel
      || dynamicLabel !== baselineDraft.dynamicLabel
      || combinedLabel !== baselineDraft.combinedLabel
      || notes !== baselineDraft.notes
    : false

  function persistDetailWidth(width: number) {
    const bounded = Math.min(760, Math.max(360, Math.round(width)))
    setDetailWidth(bounded)
    window.localStorage.setItem(`apipilot.constraintResearch.detailWidth.${runName}`, String(bounded))
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (!selectedDetail) return
      const tagName = event.target instanceof HTMLElement ? event.target.tagName : ''
      const isEditing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(tagName)
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault()
        handleSaveLabels()
        return
      }
      if (isEditing) return
      if (event.altKey && event.key.toLowerCase() === 'j') {
        event.preventDefault()
        selectNextPair()
      }
      if (event.altKey && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        selectPreviousPair()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  })

  const columns = useMemo<GridColDef<ConstraintResearchEntryResponse>[]>(
    () => [
      { field: 'operation_id', flex: 1, headerName: 'Operation', minWidth: 170 },
      {
        field: 'relation',
        headerName: 'Relation',
        minWidth: 190,
        renderCell: (params) => <CombinationRelationBadge relation={params.row.relation} />,
      },
      {
        field: 'status',
        headerName: 'Status',
        minWidth: 150,
        renderCell: (params) => <CombinationStatusBadge status={params.row.status} />,
      },
      { field: 'runtime_recommendation', headerName: 'Runtime recommendation', minWidth: 220 },
      {
        field: 'static_label',
        headerName: 'Static label',
        minWidth: 150,
        sortable: false,
        renderCell: (params) => <ResearchLabelChip label="Static" value={params.row.static_label} />,
      },
      {
        field: 'dynamic_label',
        headerName: 'Dynamic label',
        minWidth: 160,
        sortable: false,
        renderCell: (params) => <ResearchLabelChip label="Dynamic" value={params.row.dynamic_label} />,
      },
      {
        field: 'combined_label',
        headerName: 'Combined label',
        minWidth: 170,
        sortable: false,
        renderCell: (params) => <ResearchLabelChip label="Combined" value={params.row.combined_label ?? 'None'} />,
      },
      { field: 'evidence_case_count', headerName: 'Evidence', minWidth: 120 },
      { field: 'invalid_case_count', headerName: 'Invalid', minWidth: 110 },
      {
        field: 'metric_included',
        headerName: 'Metrics',
        minWidth: 130,
        renderCell: (params) => (
          <Chip
            label={params.row.metric_included ? 'Included' : 'Excluded'}
            size="small"
            variant={params.row.metric_included ? 'outlined' : 'filled'}
          />
        ),
      },
      { field: 'property_path', flex: 1, headerName: 'Property path', minWidth: 200 },
      { field: 'static_constraint', flex: 1.4, headerName: 'Static constraint', minWidth: 280 },
      { field: 'dynamic_constraint', flex: 1.4, headerName: 'Dynamic constraint', minWidth: 280 },
    ],
    [],
  )

  function handleSaveLabels() {
    if (!selectedDetail || !isDirty) return
    updateLabelsMutation.mutate({
      combinationId: selectedDetail.research_pair_id,
      runName,
      data: {
        combined_label: selectedCombinedLabel,
        dynamic_label: dynamicLabel,
        notes,
        static_label: staticLabel,
      },
    })
  }

  function updateSelectedDraft(patch: Partial<LabelDraft>) {
    if (!selectedDetail) return
    const currentDraft: LabelDraft = {
      combinedLabel,
      dynamicLabel,
      notes,
      staticLabel,
    }
    setLabelDrafts((current) => ({
      ...current,
      [selectedDetail.research_pair_id]: {
        ...currentDraft,
        ...patch,
      },
    }))
    setSaveMessage(null)
  }

  function selectPreviousPair() {
    if (activeRowIndex <= 0) return
    setSelectedPairId(rows[activeRowIndex - 1].research_pair_id)
    setSaveMessage(null)
  }

  function selectNextPair() {
    if (activeRowIndex < 0 || activeRowIndex >= rows.length - 1) return
    setSelectedPairId(rows[activeRowIndex + 1].research_pair_id)
    setSaveMessage(null)
  }

  return (
    <Stack spacing={2}>
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={1.5}
        sx={{ alignItems: { md: 'center' }, justifyContent: 'space-between' }}
      >
        <Stack spacing={0.5}>
          <Typography variant="h4">Constraint research review</Typography>
          <Typography color="text.secondary" variant="body2">
            Label static, dynamic, and combined constraints from canonical CSV state. Runtime cases are evidence, not proof.
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
          <Button href={`/runs/${encodedRunName}/constraints?constraintTab=combination&constraintsView=table`} variant="outlined">
            Back to Combination table
          </Button>
          <Button
            component="a"
            href={`/api/v1/runs/${encodedRunName}/constraints/research/labels.csv`}
            variant="contained"
          >
            Download CSV
          </Button>
          <Button
            disabled={!activePairId}
            onClick={() => setIsDetailOpen((open) => !open)}
            variant="outlined"
          >
            {isDetailOpen ? 'Hide detail' : 'Show detail'}
          </Button>
        </Stack>
      </Stack>

      <QueryState
        empty={false}
        error={summaryQuery.error}
        isError={summaryQuery.isError}
        isLoading={summaryQuery.isLoading}
        onRetry={() => void summaryQuery.refetch()}
      >
        {summary ? <ResearchSummaryCards summary={summary} /> : null}
      </QueryState>

      <Box
        sx={{
          alignItems: 'start',
          display: 'grid',
          gap: 2,
          gridTemplateColumns: {
            xs: '1fr',
            lg: isDetailOpen ? `minmax(0, 1fr) minmax(360px, ${detailWidth}px)` : 'minmax(0, 1fr)',
          },
        }}
      >
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={2}>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
              <TextField
                label="Relation"
                onChange={(event) => {
                  setRelation(event.target.value)
                  setSaveMessage(null)
                }}
                select
                size="small"
                value={relation}
              >
                <MenuItem value="">All relations</MenuItem>
                {Object.keys(summary?.relation_counts ?? {}).map((key) => (
                  <MenuItem key={key} value={key}>{key}</MenuItem>
                ))}
              </TextField>
              <TextField
                label="Runtime recommendation"
                onChange={(event) => {
                  setRuntimeRecommendation(event.target.value)
                  setSaveMessage(null)
                }}
                select
                size="small"
                value={runtimeRecommendation}
              >
                <MenuItem value="">All recommendations</MenuItem>
                {Object.keys(summary?.runtime_recommendation_counts ?? {}).map((key) => (
                  <MenuItem key={key} value={key}>{key}</MenuItem>
                ))}
              </TextField>
              <TextField
                label="Invalid reason"
                onChange={(event) => {
                  setInvalidReason(event.target.value)
                  setSaveMessage(null)
                }}
                select
                size="small"
                value={invalidReason}
              >
                <MenuItem value="">All invalid reasons</MenuItem>
                {Object.keys(summary?.invalid_runtime_counts ?? {}).map((key) => (
                  <MenuItem key={key} value={key}>{key}</MenuItem>
                ))}
              </TextField>
              <TextField
                label="Label state"
                onChange={(event) => {
                  setLabelState(event.target.value)
                  setSaveMessage(null)
                }}
                select
                size="small"
                value={labelState}
              >
                <MenuItem value="">All labels</MenuItem>
                <MenuItem value="labeled">Labeled</MenuItem>
                <MenuItem value="unlabeled">Unlabeled</MenuItem>
              </TextField>
              <TextField
                label="CSV row state"
                onChange={(event) => {
                  setOrphanedFilter(event.target.value as 'active' | 'orphaned' | 'all')
                  setSaveMessage(null)
                }}
                select
                size="small"
                value={orphanedFilter}
              >
                <MenuItem value="active">Active pairs</MenuItem>
                <MenuItem value="orphaned">Orphaned labels</MenuItem>
                <MenuItem value="all">All CSV rows</MenuItem>
              </TextField>
            </Stack>

              <QueryState
                empty={rows.length === 0}
                emptyDescription="No research pairs match the current filters."
                emptyTitle="No research pairs"
                error={entriesQuery.error}
                isError={entriesQuery.isError}
                isLoading={entriesQuery.isLoading}
                onRetry={() => void entriesQuery.refetch()}
              >
                <ServerDataGridPanel
                  ariaLabel="constraint research pairs"
                  columns={columns}
                  getRowId={(row) => row.research_pair_id}
                  getRowClassName={(params) =>
                    params.row.research_pair_id === activePairId || params.row.combination_id === activePairId
                      ? 'constraint-research-row--active'
                      : ''
                  }
                  loading={entriesQuery.isFetching}
                  onPaginationModelChange={setPaginationModel}
                  onRowClick={(params) => setSelectedPairId(params.row.research_pair_id)}
                  paginationModel={paginationModel}
                  rowCount={entriesQuery.data?.pagination.total ?? 0}
                  rows={rows}
                  sortModel={[]}
                  sx={{
                    '& .constraint-research-row--active': {
                      bgcolor: (theme) => theme.palette.action.selected,
                    },
                  }}
                  tableLayout={{ page: 'constraints', runName, tableId: 'constraint-research-pairs' }}
                />
              </QueryState>
            </Stack>
          </CardContent>
        </Card>

        {isDetailOpen ? (
          <Box
            onMouseUp={(event) => persistDetailWidth(event.currentTarget.getBoundingClientRect().width)}
            sx={{
              maxWidth: { lg: 760 },
              minWidth: { lg: 360 },
              overflow: 'auto',
              position: { lg: 'sticky' },
              resize: { lg: 'horizontal' },
              top: { lg: 16 },
              width: { lg: detailWidth },
            }}
          >
            {activePairId ? (
            <QueryState
              empty={false}
              error={detailQuery.error}
              isError={detailQuery.isError}
              isLoading={detailQuery.isLoading}
              onRetry={() => void detailQuery.refetch()}
            >
              {selectedDetail ? (
                <ResearchDetailPanel
                  combinedLabel={combinedLabel}
                  detail={selectedDetail}
                  dynamicLabel={dynamicLabel}
                  hasNext={activeRowIndex >= 0 && activeRowIndex < rows.length - 1}
                  hasPrevious={activeRowIndex > 0}
                  isDirty={isDirty}
                  isSaving={updateLabelsMutation.isPending}
                  notes={notes}
                  onCombinedLabelChange={(value) => updateSelectedDraft({ combinedLabel: value })}
                  onDynamicLabelChange={(value) => updateSelectedDraft({ dynamicLabel: value })}
                  onNext={selectNextPair}
                  onNotesChange={(value) => updateSelectedDraft({ notes: value })}
                  onPrevious={selectPreviousPair}
                  onSave={handleSaveLabels}
                  onStaticLabelChange={(value) => updateSelectedDraft({ staticLabel: value })}
                  saveError={updateLabelsMutation.error}
                  saveMessage={saveMessage}
                  staticLabel={staticLabel}
                />
              ) : null}
            </QueryState>
            ) : (
              <Alert severity="info">Select a pair to inspect evidence and edit researcher labels.</Alert>
            )}
          </Box>
        ) : null}
      </Box>
    </Stack>
  )
}

function ResearchSummaryCards({ summary }: { summary: ConstraintResearchSummaryResponse }) {
  const staticMetrics = metricFor(summary, 'static_label', 'static')
  const dynamicMetrics = metricFor(summary, 'dynamic_label', 'dynamic')
  const combinedMetrics = metricFor(summary, 'combined_label', 'combined')
  const invalidRuntimeCount = countValues(summary.invalid_runtime_counts)

  return (
    <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', md: '1.2fr 1.2fr 1fr 1fr 1fr' } }}>
      <Box>
        <MetricCard label="Pairs" value={summary.pair_count} helper={`${summary.evidence_case_count} evidence cases`} />
      </Box>
      <Box>
        <MetricCard label="Invalid runtime cases" value={invalidRuntimeCount} helper="Tracked separately from labels" />
      </Box>
      <Box>
        <MetricCard label="Static precision" value={formatMetric(staticMetrics?.precision)} helper={`${staticMetrics?.evaluated ?? 0} evaluated`} />
      </Box>
      <Box>
        <MetricCard label="Dynamic precision" value={formatMetric(dynamicMetrics?.precision)} helper={`${dynamicMetrics?.evaluated ?? 0} evaluated`} />
      </Box>
      <Box>
        <MetricCard label="Combined precision" value={formatMetric(combinedMetrics?.precision)} helper={`${combinedMetrics?.evaluated ?? 0} evaluated`} />
      </Box>
    </Box>
  )
}

function metricFor(summary: ConstraintResearchSummaryResponse, primaryKey: string, fallbackKey: string) {
  return summary.source_metrics[primaryKey] ?? summary.source_metrics[fallbackKey]
}

function countValues(values: Record<string, number>) {
  return Object.values(values).reduce((total, count) => total + count, 0)
}

function MetricCard({ helper, label, value }: { helper: string; label: string; value: number | string }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography color="text.secondary" variant="caption">{label}</Typography>
        <Typography variant="h5">{value}</Typography>
        <Typography color="text.secondary" variant="body2">{helper}</Typography>
      </CardContent>
    </Card>
  )
}

type ResearchDetailPanelProps = {
  combinedLabel: CombinedResearchLabel
  detail: ConstraintResearchDetailResponse
  dynamicLabel: ResearchLabel
  hasNext: boolean
  hasPrevious: boolean
  isDirty: boolean
  isSaving: boolean
  notes: string
  onCombinedLabelChange: (value: CombinedResearchLabel) => void
  onDynamicLabelChange: (value: ResearchLabel) => void
  onNext: () => void
  onNotesChange: (value: string) => void
  onPrevious: () => void
  onSave: () => void
  onStaticLabelChange: (value: ResearchLabel) => void
  saveError: unknown
  saveMessage: string | null
  staticLabel: ResearchLabel
}

function ResearchDetailPanel({
  combinedLabel,
  detail,
  dynamicLabel,
  hasNext,
  hasPrevious,
  isDirty,
  isSaving,
  notes,
  onCombinedLabelChange,
  onDynamicLabelChange,
  onNext,
  onNotesChange,
  onPrevious,
  onSave,
  onStaticLabelChange,
  saveError,
  saveMessage,
  staticLabel,
}: ResearchDetailPanelProps) {
  const evidenceCases = useMemo(
    () => [...detail.evidence_cases].sort(compareEvidenceCases),
    [detail.evidence_cases],
  )

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} sx={{ justifyContent: 'space-between' }}>
            <Stack spacing={0.5}>
              <Typography variant="h5">{detail.property_path}</Typography>
              <Typography color="text.secondary" variant="body2">
                {detail.operation_id} · Updated {formatDateTime(detail.updated_at)}
              </Typography>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
              <CombinationRelationBadge relation={detail.relation} />
              <CombinationStatusBadge status={detail.status} />
              <Chip label={`Runtime ${detail.runtime_recommendation}`} size="small" variant="outlined" />
            </Stack>
          </Stack>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography color="text.secondary" variant="caption">
              Pair {detail.research_pair_id} · Trace {detail.combination_id}
            </Typography>
            <Stack direction="row" spacing={1}>
              <Button disabled={!hasPrevious} onClick={onPrevious} size="small" variant="outlined">
                Previous pair
              </Button>
              <Button disabled={!hasNext} onClick={onNext} size="small" variant="outlined">
                Next pair
              </Button>
            </Stack>
          </Stack>

          <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' } }}>
            <Box>
              <ConstraintBox label="Static constraint" value={detail.static_constraint} />
            </Box>
            <Box>
              <ConstraintBox label="Dynamic constraint" value={detail.dynamic_constraint} />
            </Box>
            <Box>
              <ConstraintBox label="Combined final" value={detail.final_constraint || 'No combined final'} />
            </Box>
          </Box>

          <Box
            aria-label="Spec context"
            role="region"
            sx={{
              bgcolor: 'background.default',
              border: (theme) => `1px solid ${theme.apiTesting.border.default}`,
              borderRadius: 1,
              p: 1.5,
            }}
          >
            <Stack spacing={1}>
              <Stack spacing={0.5}>
                <Typography sx={{ fontWeight: 700 }} variant="body2">OpenAPI operation excerpt</Typography>
                <Typography color="text.secondary" variant="body2">
                  Operation {detail.operation_id}; property {detail.property_path}; trace id {detail.combination_id}.
                </Typography>
              </Stack>
              <SpecExcerptAccordion excerpt={detail.operation_spec_excerpt} />
            </Stack>
          </Box>

          <Divider />

          <Stack aria-label="Research label editor" role="region" spacing={1}>
            <Typography variant="h6">Research labels</Typography>
            <Typography color="text.secondary" variant="body2">
              Human-edited CSV labels are canonical for paper metrics. Suggested labels are deterministic hints from runtime evidence.
            </Typography>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
              <LabelSelect
                helper={`Suggested: ${detail.suggested_static_label}`}
                label="Static label"
                onChange={onStaticLabelChange}
                value={staticLabel}
              />
              <LabelSelect
                helper={`Suggested: ${detail.suggested_dynamic_label}`}
                label="Dynamic label"
                onChange={onDynamicLabelChange}
                value={dynamicLabel}
              />
              <TextField
                helperText={`Suggested: ${detail.suggested_combined_label}`}
                label="Combined label"
                onChange={(event) => onCombinedLabelChange(asCombinedResearchLabel(event.target.value))}
                select
                size="small"
                sx={{ minWidth: { md: 180 } }}
                value={combinedLabel}
              >
                <MenuItem value="">No combined label</MenuItem>
                {LABEL_OPTIONS.map((option) => (
                  <MenuItem key={option} value={option}>{option}</MenuItem>
                ))}
              </TextField>
            </Stack>
            <TextField
              label="Research notes"
              multiline
              minRows={3}
              onChange={(event) => onNotesChange(event.target.value)}
              value={notes}
            />
            {saveError ? <Alert severity="error">Could not save labels. Check the backend response and retry.</Alert> : null}
            {saveMessage ? <Alert severity="success">{saveMessage}</Alert> : null}
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
              <Button disabled={!isDirty || isSaving} onClick={onSave} variant="contained">
                Save CSV labels
              </Button>
              <Typography color="text.secondary" variant="body2">
                {isDirty ? 'Unsaved changes' : 'No unsaved label changes'}
              </Typography>
            </Stack>
          </Stack>

          <Divider />

          <Stack aria-label="Evidence cases" role="region" spacing={1}>
            <Typography variant="h6">Evidence cases</Typography>
            <Typography color="text.secondary" variant="body2">
              Evidence helps triage labels and invalid runtime taxonomy. It should not be treated as formal proof.
            </Typography>
            {evidenceCases.length === 0 ? (
              <Alert severity="info">No runtime evidence has been generated for this pair yet.</Alert>
            ) : (
              evidenceCases.map((evidence, index) => (
                <EvidenceCard
                  evidence={evidence}
                  key={evidence.case_id}
                  summaryLabel={index === 0 ? 'Visual evidence summary' : 'Evidence summary'}
                />
              ))
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

function ResearchLabelChip({ label, value }: { label: string; value: string }) {
  const normalized = value || 'None'
  const color = normalized === 'TP' ? 'success' : normalized === 'FP' ? 'error' : 'default'
  return (
    <Chip
      color={color}
      label={`${label} ${normalized}`}
      size="small"
      variant={normalized === 'UNSURE' || normalized === 'None' ? 'outlined' : 'filled'}
    />
  )
}

function LabelSelect({
  helper,
  label,
  onChange,
  value,
}: {
  helper: string
  label: string
  onChange: (value: ResearchLabel) => void
  value: ResearchLabel
}) {
  return (
    <TextField
      helperText={helper}
      label={label}
      onChange={(event) => onChange(asResearchLabel(event.target.value))}
      select
      size="small"
      sx={{ minWidth: { md: 180 } }}
      value={value}
    >
      {LABEL_OPTIONS.map((option) => (
        <MenuItem key={option} value={option}>{option}</MenuItem>
      ))}
    </TextField>
  )
}

function ConstraintBox({ label, value }: { label: string; value: string }) {
  return (
    <Box
      sx={{
        border: (theme) => `1px solid ${theme.apiTesting.border.default}`,
        borderRadius: 1,
        minHeight: 96,
        p: 1.5,
      }}
    >
      <Typography color="text.secondary" variant="caption">{label}</Typography>
      <Typography sx={{ overflowWrap: 'anywhere' }} variant="body2">{value}</Typography>
    </Box>
  )
}

function SpecExcerptAccordion({ excerpt }: { excerpt: unknown }) {
  const [expanded, setExpanded] = useState(false)
  const [rawExpanded, setRawExpanded] = useState(false)
  const record = asRecord(excerpt)
  const method = valueAsString(record.method).toUpperCase()
  const path = valueAsString(record.path)
  const summary = valueAsString(record.summary)

  return (
    <Accordion
      disableGutters
      expanded={expanded}
      onChange={(_event, nextExpanded) => setExpanded(nextExpanded)}
      variant="outlined"
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack spacing={0.25}>
          <Typography sx={{ fontWeight: 700 }} variant="body2">Show OpenAPI spec excerpt</Typography>
          <Typography color="text.secondary" variant="caption">
            {[method, path].filter(Boolean).join(' · ') || 'Spec excerpt unavailable'}
          </Typography>
        </Stack>
      </AccordionSummary>
      {expanded ? (
        <AccordionDetails>
          {Object.keys(record).length === 0 ? (
            <Alert severity="info">No operation spec excerpt is available for this pair.</Alert>
          ) : (
            <Stack spacing={1}>
              {summary ? <Typography variant="body2">{summary}</Typography> : null}
              <Typography color="text.secondary" variant="body2">
                {[method, path].filter(Boolean).join(' ')}
              </Typography>
              <Accordion
                disableGutters
                expanded={rawExpanded}
                onChange={(_event, nextExpanded) => setRawExpanded(nextExpanded)}
                variant="outlined"
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography sx={{ fontWeight: 700 }} variant="body2">View raw spec JSON</Typography>
                </AccordionSummary>
                {rawExpanded ? (
                  <AccordionDetails>
                    <JsonBlock label="Operation spec JSON" value={excerpt} />
                  </AccordionDetails>
                ) : null}
              </Accordion>
            </Stack>
          )}
        </AccordionDetails>
      ) : null}
    </Accordion>
  )
}

function EvidenceCard({
  evidence,
  summaryLabel,
}: {
  evidence: ConstraintResearchEvidenceCaseResponse
  summaryLabel: string
}) {
  const [rawExpanded, setRawExpanded] = useState(false)
  const request = asRecord(evidence.request_summary)
  const response = asRecord(evidence.response_summary)
  const methodPath = requestMethodPath(request)
  const statusCode = valueAsString(response.status_code)

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
          <Typography sx={{ fontWeight: 700 }} variant="body2">{evidence.case_id}</Typography>
          <Chip label={evidence.runtime_verdict} size="small" variant="outlined" />
          <Chip label={evidence.runtime_recommendation} size="small" variant="outlined" />
          {evidence.invalid_reason ? <Chip color="warning" label={evidence.invalid_reason} size="small" /> : null}
          {evidence.planner_status ? <Chip label={`Planner ${evidence.planner_status}`} size="small" variant="outlined" /> : null}
          {evidence.weak_evidence ? <Chip color="warning" label="Weak evidence" size="small" variant="outlined" /> : null}
          </Stack>
          <Box>
            <Typography sx={{ fontWeight: 700 }} variant="body2">{summaryLabel}</Typography>
            <Typography color="text.secondary" variant="body2">
              {methodPath || 'Request shape unavailable'}
              {statusCode ? ` · Response ${statusCode}` : ''}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              Runtime recommendation: {evidence.runtime_recommendation || 'INCONCLUSIVE'}; support, not proof.
            </Typography>
          </Box>
          {evidence.invalid_detail ? (
            <Alert severity="warning">{evidence.invalid_detail}</Alert>
          ) : null}
          {evidence.planner_error_kind ? (
            <Alert severity="info">Planner issue: {evidence.planner_error_kind}. Treat this as weak diagnostic evidence.</Alert>
          ) : null}
          <Accordion
            disableGutters
            expanded={rawExpanded}
            onChange={(_event, nextExpanded) => setRawExpanded(nextExpanded)}
            variant="outlined"
          >
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography sx={{ fontWeight: 700 }} variant="body2">View raw</Typography>
            </AccordionSummary>
            {rawExpanded ? (
              <AccordionDetails>
                <Box sx={{ display: 'grid', gap: 1.5, gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' } }}>
                  <Box>
                    <JsonBlock label="Request summary" value={evidence.request_summary} />
                  </Box>
                  <Box>
                    <JsonBlock label="Response summary" value={evidence.response_summary} />
                  </Box>
                  <Box>
                    <JsonBlock label="Execution metadata" value={evidence.execution_metadata} />
                  </Box>
                </Box>
              </AccordionDetails>
            ) : null}
          </Accordion>
        </Stack>
      </CardContent>
    </Card>
  )
}

function compareEvidenceCases(
  left: ConstraintResearchEvidenceCaseResponse,
  right: ConstraintResearchEvidenceCaseResponse,
) {
  const leftInvalid = left.invalid_reason ? 0 : 1
  const rightInvalid = right.invalid_reason ? 0 : 1
  if (leftInvalid !== rightInvalid) return leftInvalid - rightInvalid
  return left.case_id.localeCompare(right.case_id)
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <Stack spacing={0.5}>
      <Typography color="text.secondary" variant="caption">{label}</Typography>
      <Box
        component="pre"
        sx={{
          bgcolor: 'background.default',
          border: (theme) => `1px solid ${theme.apiTesting.border.default}`,
          borderRadius: 1,
          fontSize: 12,
          m: 0,
          maxHeight: 220,
          overflow: 'auto',
          p: 1,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {formatJson(value)}
      </Box>
    </Stack>
  )
}

function asResearchLabel(value: unknown): ResearchLabel {
  return LABEL_OPTIONS.includes(value as ResearchLabel) ? (value as ResearchLabel) : 'UNSURE'
}

function asCombinedResearchLabel(value: unknown): CombinedResearchLabel {
  return value === 'TP' || value === 'FP' || value === 'UNSURE' ? value : ''
}

function draftFromResearchEntry(entry: Pick<
  ConstraintResearchEntryResponse,
  'combined_label' | 'dynamic_label' | 'notes' | 'static_label'
>): LabelDraft {
  return {
    combinedLabel: asCombinedResearchLabel(entry.combined_label),
    dynamicLabel: asResearchLabel(entry.dynamic_label),
    notes: entry.notes,
    staticLabel: asResearchLabel(entry.static_label),
  }
}

function formatMetric(value: number | null | undefined) {
  if (value === null || value === undefined) return 'n/a'
  return `${Math.round(value * 100)}%`
}

function formatJson(value: unknown) {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'string') return value
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function valueAsString(value: unknown) {
  if (value === null || value === undefined) return ''
  return String(value)
}

function requestMethodPath(request: Record<string, unknown>) {
  const method = valueAsString(request.method).toUpperCase()
  const path = valueAsString(request.path)
  return [method, path].filter(Boolean).join(' ')
}
