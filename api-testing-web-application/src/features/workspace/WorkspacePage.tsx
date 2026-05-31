import BookmarkAddIcon from '@mui/icons-material/BookmarkAdd'
import DownloadIcon from '@mui/icons-material/Download'
import SaveIcon from '@mui/icons-material/Save'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useCallback, useMemo, useState } from 'react'

import type {
  GraphExplorerEdgeResponse,
  OperationExplorerEntryResponse,
  SortOrder,
} from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { useRunWorkspaceSearchActions } from '../../shared/lib/searchActions'
import {
  loadBookmarks,
  loadLayoutPresets,
  loadRecentEntities,
  loadSavedViews,
  loadWorkspaceNotes,
  saveBookmarks,
  saveLayoutPresets,
  saveRecentEntities,
  saveSavedViews,
  saveWorkspaceNotes,
  upsertLayoutPreset,
  upsertBookmark,
  upsertRecentEntity,
  upsertSavedView,
  upsertWorkspaceNote,
  type RecentEntitySource,
  type SavedView,
  type WorkspaceBookmark,
  type WorkspaceEntityType,
  type WorkspaceLayoutPreset,
  type WorkspaceNote,
} from '../../shared/lib/workspaceStorage'
import { DebouncedTextField } from '../../shared/ui/DebouncedTextField'
import { DesktopLayoutPresetControl } from '../../shared/ui/DesktopLayoutPresetControl'
import { EmptyState } from '../../shared/ui/EmptyState'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { PageLearningPanel } from '../../shared/ui/Guidance'
import { PageHeader } from '../../shared/ui/PageHeader'
import { Panel } from '../../shared/ui/Panel'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { HttpMethodBadge } from '../../shared/ui/SemanticBadges'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { useGraphEdgeDetail, useGraphEdges, useGraphSequenceDetail, useDependencyGraph } from '../graph/api'
import {
  toOperationExplorerParams,
  useOperationExplorerDetail,
  useOperationExplorerEntries,
} from '../operations/api'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'

export type WorkspacePageSearch = {
  edgeId?: string
  limit: number
  offset: number
  operationId?: string
  operationKey?: string
  q?: string
  savedViewId?: string
  sequenceId?: string
  sortBy?: string
  sortOrder?: SortOrder
  workspaceView?: 'cockpit' | 'compare' | 'graph' | 'operations'
}

type WorkspacePageProps = {
  runName: string
  search: WorkspacePageSearch
}

function workspacePath(runName: string) {
  return `/runs/${encodeRoutePart(runName)}/workspace`
}

function currentRouteFallback(runName: string, search: WorkspacePageSearch) {
  const params = new URLSearchParams()
  Object.entries(search).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  })
  return `${workspacePath(runName)}${params.size ? `?${params}` : ''}`
}

const workspaceLayoutColumns = {
  balanced: {
    graph: { xs: 12, lg: 5, xl: 6 },
    inspector: { xs: 12, lg: 3, xl: 3 },
    operations: { xs: 12, lg: 4, xl: 3 },
  },
  graph: {
    graph: { xs: 12, lg: 6, xl: 7 },
    inspector: { xs: 12, lg: 3, xl: 3 },
    operations: { xs: 12, lg: 3, xl: 2 },
  },
  inspector: {
    graph: { xs: 12, lg: 4, xl: 4 },
    inspector: { xs: 12, lg: 5, xl: 5 },
    operations: { xs: 12, lg: 3, xl: 3 },
  },
  table: {
    graph: { xs: 12, lg: 4, xl: 4 },
    inspector: { xs: 12, lg: 3, xl: 3 },
    operations: { xs: 12, lg: 5, xl: 5 },
  },
} satisfies Record<WorkspaceLayoutPreset, {
  graph: { xs: 12; lg: number; xl: number }
  inspector: { xs: 12; lg: number; xl: number }
  operations: { xs: 12; lg: number; xl: number }
}>

function selectedEntity({
  edgeId,
  operationId,
  operationKey,
  sequenceId,
}: WorkspacePageSearch): { entityId: string; entityType: WorkspaceEntityType; label: string } | undefined {
  if (operationKey || operationId) {
    const entityId = operationKey ?? operationId ?? ''
    return { entityId, entityType: 'operation', label: entityId }
  }
  if (edgeId) return { entityId: edgeId, entityType: 'graph-edge', label: edgeId }
  if (sequenceId) return { entityId: sequenceId, entityType: 'graph-sequence', label: sequenceId }
  return undefined
}

function SavedViewDialog({
  onClose,
  onSave,
  open,
}: {
  onClose: () => void
  onSave: (name: string) => void
  open: boolean
}) {
  const [name, setName] = useState('')

  return (
    <Dialog fullWidth maxWidth="xs" onClose={onClose} open={open}>
      <DialogTitle>Save workspace view</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          label="View name"
          onChange={(event) => setName(event.target.value)}
          sx={{ mt: 1 }}
          value={name}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          disabled={!name.trim()}
          onClick={() => {
            onSave(name)
            setName('')
          }}
          startIcon={<SaveIcon />}
          variant="contained"
        >
          Save
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export function WorkspacePage({ runName, search }: WorkspacePageProps) {
  const actions = useRunWorkspaceSearchActions()
  const [savedViews, setSavedViews] = useState<SavedView[]>(() => loadSavedViews())
  const [bookmarks, setBookmarks] = useState<WorkspaceBookmark[]>(() => loadBookmarks())
  const [notes, setNotes] = useState<WorkspaceNote[]>(() => loadWorkspaceNotes())
  const [layoutPresets, setLayoutPresets] = useState(() => loadLayoutPresets())
  const [recentEntities, setRecentEntities] = useState(() => loadRecentEntities())
  const [saveViewOpen, setSaveViewOpen] = useState(false)
  const [exportOpen, setExportOpen] = useState(false)
  const [noteDraft, setNoteDraft] = useState('')
  const sourceSelectionKey = [
    search.edgeId ?? '',
    search.operationId ?? '',
    search.operationKey ?? '',
    search.sequenceId ?? '',
  ].join('|')
  const [localSelectionOverride, setLocalSelectionOverride] = useState<{
    sourceSelectionKey: string
    value: Partial<WorkspacePageSearch>
  }>()
  const gridState = useUrlBackedGridState(search)
  const effectiveSearch = localSelectionOverride?.sourceSelectionKey === sourceSelectionKey
    ? { ...search, ...localSelectionOverride.value }
    : search
  const selected = selectedEntity(effectiveSearch)
  const runSavedViews = savedViews.filter((view) => view.runName === runName && view.page === 'workspace')
  const runBookmarks = bookmarks.filter((bookmark) => bookmark.runName === runName)
  const runNotes = notes.filter((note) => note.runName === runName)
  const runRecentEntities = recentEntities.filter((entity) => entity.runName === runName).slice(0, 8)
  const layoutPreset = layoutPresets.find((preset) => preset.runName === runName && preset.page === 'workspace')?.layout ?? 'balanced'
  const layoutColumns = workspaceLayoutColumns[layoutPreset]
  const currentNote = selected
    ? runNotes.find((note) => note.entityType === selected.entityType && note.entityId === selected.entityId)
    : undefined

  const operationParams = toOperationExplorerParams({
    limit: search.limit,
    offset: search.offset,
    q: search.q,
    sortBy: search.sortBy,
    sortOrder: search.sortOrder,
  })
  const operationsQuery = useOperationExplorerEntries(runName, operationParams)
  const graphQuery = useDependencyGraph(runName)
  const edgeRowsQuery = useGraphEdges(runName, {
    limit: 8,
    offset: 0,
    q: search.q,
  })
  const operationDetailQuery = useOperationExplorerDetail(runName, effectiveSearch.operationKey ?? '', {
    query: { enabled: Boolean(effectiveSearch.operationKey) },
  })
  const edgeDetailQuery = useGraphEdgeDetail(runName, effectiveSearch.edgeId ?? '', {
    query: { enabled: Boolean(effectiveSearch.edgeId) },
  })
  const sequenceDetailQuery = useGraphSequenceDetail(runName, effectiveSearch.sequenceId ?? '', {
    query: { enabled: Boolean(effectiveSearch.sequenceId) },
  })

  const operationRows = useMemo(() => operationsQuery.data?.items ?? [], [operationsQuery.data?.items])
  const edgeRows = useMemo(() => edgeRowsQuery.data?.items ?? [], [edgeRowsQuery.data?.items])
  const selectedOperation = operationDetailQuery.data
    ?? operationRows.find((row) => row.operation_key === effectiveSearch.operationKey || row.operation_id === effectiveSearch.operationId)

  const setLocalSelection = useCallback((value: Partial<WorkspacePageSearch>) => {
    setLocalSelectionOverride({ sourceSelectionKey, value })
  }, [sourceSelectionKey])

  const updateLayoutPreset = useCallback((layout: WorkspaceLayoutPreset) => {
    setLayoutPresets((current) => {
      const next = upsertLayoutPreset(current, {
        layout,
        page: 'workspace',
        runName,
      })
      saveLayoutPresets(next)
      return next
    })
  }, [runName])

  const recordRecentEntity = useCallback((input: {
    entityId: string
    entityType: WorkspaceEntityType
    href: string
    label: string
    source?: RecentEntitySource
  }) => {
    setRecentEntities((current) => {
      const next = upsertRecentEntity(current, {
        ...input,
        runName,
        source: input.source ?? 'workspace',
      })
      saveRecentEntities(next)
      return next
    })
  }, [runName])

  const selectOperationRow = useCallback((row: OperationExplorerEntryResponse) => {
    setLocalSelection({
      edgeId: undefined,
      operationId: row.operation_id,
      operationKey: row.operation_key,
      sequenceId: undefined,
    })
    recordRecentEntity({
      entityId: row.operation_key,
      entityType: 'operation',
      href: `${workspacePath(runName)}?operationKey=${encodeURIComponent(row.operation_key)}`,
      label: row.display_operation_id ?? row.operation_id,
    })
    actions.selectOperation(row.operation_key, row.operation_id)
  }, [actions, recordRecentEntity, runName, setLocalSelection])

  const selectEdgeRow = useCallback((edge: GraphExplorerEdgeResponse) => {
    setLocalSelection({
      edgeId: edge.edge_id,
      operationId: undefined,
      operationKey: undefined,
      sequenceId: undefined,
    })
    recordRecentEntity({
      entityId: edge.edge_id,
      entityType: 'graph-edge',
      href: `${workspacePath(runName)}?edgeId=${encodeURIComponent(edge.edge_id)}`,
      label: `${edge.from_operation_id} to ${edge.to_operation_id}`,
    })
    actions.selectEdge(edge.edge_id)
  }, [actions, recordRecentEntity, runName, setLocalSelection])

  const selectFirstRiskyOperation = useCallback(() => {
    const operation = operationRows.find((row) => row.has_failures) ?? operationRows[0]
    if (operation) selectOperationRow(operation)
  }, [operationRows, selectOperationRow])

  const operationColumns = useMemo<GridColDef<OperationExplorerEntryResponse>[]>(
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
              selectOperationRow(params.row)
            }}
            size="small"
          >
            {params.row.display_operation_id ?? params.row.operation_id}
          </Button>
        ),
      },
      {
        field: 'http_method',
        headerName: 'Method',
        minWidth: 112,
        renderCell: (params) => <HttpMethodBadge method={params.row.http_method} />,
      },
      { field: 'path_template', flex: 1, headerName: 'Path', minWidth: 160 },
      { field: 'constraint_count', headerName: 'Constraints', minWidth: 120 },
      { field: 'test_case_count', headerName: 'Tests', minWidth: 90 },
    ],
    [selectOperationRow],
  )

  function saveCurrentView(name: string) {
    const nextViews = upsertSavedView(savedViews, {
      name: name.trim(),
      page: 'workspace',
      route: typeof window === 'undefined' ? currentRouteFallback(runName, search) : `${window.location.pathname}${window.location.search}`,
      runName,
      search,
    })
    setSavedViews(nextViews)
    saveSavedViews(nextViews)
    setSaveViewOpen(false)
  }

  function bookmarkSelected() {
    if (!selected) return
    const href = `${workspacePath(runName)}?${new URLSearchParams({
      [selected.entityType === 'operation' ? 'operationKey' : selected.entityType === 'graph-edge' ? 'edgeId' : 'sequenceId']:
        selected.entityId,
    })}`
    const nextBookmarks = upsertBookmark(bookmarks, {
      entityId: selected.entityId,
      entityType: selected.entityType,
      href,
      label: selected.label,
      runName,
    })
    setBookmarks(nextBookmarks)
    saveBookmarks(nextBookmarks)
  }

  function saveSelectedNote() {
    if (!selected) return
    const nextNotes = upsertWorkspaceNote(notes, {
      entityId: selected.entityId,
      entityType: selected.entityType,
      note: noteDraft || currentNote?.note || '',
      runName,
    })
    setNotes(nextNotes)
    saveWorkspaceNotes(nextNotes)
  }

  function applySavedView(view: SavedView) {
    setLocalSelectionOverride(undefined)
    actions.applySavedView(view.search, view.id)
  }

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
            <DesktopLayoutPresetControl onChange={updateLayoutPreset} value={layoutPreset} />
            <Button onClick={() => setSaveViewOpen(true)} startIcon={<SaveIcon />} variant="outlined">
              Save view
            </Button>
            <Button onClick={() => setExportOpen(true)} startIcon={<DownloadIcon />} variant="outlined">
              Export workspace
            </Button>
          </Stack>
        }
        eyebrow="Desktop investigation"
        subtitle="Triage operations, graph evidence, pinned bookmarks, and local notes in one run-scoped workspace."
        title="Investigation Workspace"
        {...tourAnchor(TOUR_ANCHORS.workspaceHeader)}
      />

      <PageLearningPanel
        sections={[
          {
            body: 'Use the operations pane to choose an endpoint, then keep graph evidence and inspector context visible while you work.',
            title: 'Desktop investigation flow',
          },
          {
            body: 'Saved views, notes, bookmarks, and layout presets stay local to this browser unless you explicitly include them in export.',
            title: 'Local-only context',
          },
        ]}
      />

      <Grid container spacing={2}>
        <Grid size={layoutColumns.operations}>
          <Panel
            actions={
              <Button disabled={!selected} onClick={bookmarkSelected} size="small" startIcon={<BookmarkAddIcon />}>
                Bookmark selected
              </Button>
            }
            subtitle="URL-backed filters with local saved views."
            title="Operations"
            {...tourAnchor(TOUR_ANCHORS.workspaceOperations)}
          >
            <Stack spacing={1.5}>
              <DebouncedTextField
                fullWidth
                label="Workspace search"
                onDebouncedChange={actions.setQuery}
                size="small"
                value={search.q ?? ''}
              />
              {runSavedViews.length > 0 ? (
                <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                  {runSavedViews.map((view) => (
                    <Button key={view.id} onClick={() => applySavedView(view)} size="small" variant="outlined">
                      {view.name}
                    </Button>
                  ))}
                </Stack>
              ) : null}
              <QueryState
                empty={operationRows.length === 0}
                error={operationsQuery.error}
                isError={operationsQuery.isError}
                isLoading={operationsQuery.isLoading}
                onRetry={() => void operationsQuery.refetch()}
              >
                <ServerDataGridPanel
                  ariaLabel="workspace operations"
                  columns={operationColumns}
                  copyCellOnDoubleClick
                  getRowId={(row) => row.operation_key}
                  loading={operationsQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onRowClick={(params) => selectOperationRow(params.row)}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={operationsQuery.data?.pagination.total ?? 0}
                  rows={operationRows}
                  sortModel={gridState.sortModel}
                  tableLayout={{ page: 'workspace', runName, tableId: 'operations' }}
                />
              </QueryState>
            </Stack>
          </Panel>
        </Grid>

        <Grid size={layoutColumns.graph}>
          <Panel
            title="Graph focus"
            subtitle="Performance-first dependency evidence lens."
            {...tourAnchor(TOUR_ANCHORS.workspaceGraphFocus)}
          >
            <Box aria-label="workspace graph focus" role="region">
              <QueryState
                empty={(graphQuery.data?.nodes.length ?? 0) === 0}
                error={graphQuery.error}
                isError={graphQuery.isError}
                isLoading={graphQuery.isLoading}
                onRetry={() => void graphQuery.refetch()}
              >
                <Stack spacing={2}>
                  <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                    <Chip label={`${graphQuery.data?.nodes.length ?? 0} nodes`} />
                    <Chip label={`${graphQuery.data?.edges.length ?? 0} graph edges`} variant="outlined" />
                    <Chip label="Legend: final edges are high-confidence dependency evidence" variant="outlined" />
                  </Stack>
                  <Grid container spacing={1.5}>
                    {edgeRows.map((edge: GraphExplorerEdgeResponse) => (
                      <Grid key={edge.edge_id} size={{ xs: 12, md: 6 }}>
                        <Card variant="outlined">
                          <CardContent>
                            <Stack spacing={1}>
                              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                                <Chip label={edge.edge_status} size="small" />
                                <Chip label={`${edge.evidence_count} evidence`} size="small" variant="outlined" />
                              </Stack>
                              <Typography sx={{ fontWeight: 800, overflowWrap: 'anywhere' }} variant="body2">
                                {edge.from_operation_id} → {edge.to_operation_id}
                              </Typography>
                              <Button
                                onClick={() => selectEdgeRow(edge)}
                                size="small"
                                variant="outlined"
                              >
                                Inspect edge
                              </Button>
                            </Stack>
                          </CardContent>
                        </Card>
                      </Grid>
                    ))}
                  </Grid>
                </Stack>
              </QueryState>
            </Box>
          </Panel>
        </Grid>

        <Grid size={layoutColumns.inspector}>
          <Panel
            title="Inspector"
            subtitle="Entity details, graph context, and local notes."
            {...tourAnchor(TOUR_ANCHORS.workspaceInspector)}
          >
            <Stack spacing={2}>
              {selectedOperation ? (
                <Stack spacing={1}>
                  <Typography color="text.secondary" variant="caption">
                    Selected operation
                  </Typography>
                  <Typography sx={{ fontWeight: 800 }} variant="h3">
                    {selectedOperation.display_operation_id ?? selectedOperation.operation_id}
                  </Typography>
                  <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="body2">
                    {selectedOperation.operation_key}
                  </Typography>
                  <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                    <Chip label={`${selectedOperation.constraint_count} constraints`} size="small" />
                    <Chip label={`${selectedOperation.test_case_count} tests`} size="small" />
                    <Chip label={selectedOperation.has_failures ? 'Failures' : 'Clean'} size="small" />
                  </Stack>
                </Stack>
              ) : effectiveSearch.edgeId && edgeDetailQuery.data ? (
                <Stack spacing={1}>
                  <Typography color="text.secondary" variant="caption">
                    Selected edge
                  </Typography>
                  <Typography sx={{ fontWeight: 800, overflowWrap: 'anywhere' }} variant="h3">
                    {edgeDetailQuery.data.from_operation_id} → {edgeDetailQuery.data.to_operation_id}
                  </Typography>
                  <Chip label={`${edgeDetailQuery.data.evidence_count} evidence items`} size="small" />
                </Stack>
              ) : effectiveSearch.sequenceId && sequenceDetailQuery.data ? (
                <Stack spacing={1}>
                  <Typography color="text.secondary" variant="caption">
                    Selected sequence
                  </Typography>
                  <Typography sx={{ fontWeight: 800, overflowWrap: 'anywhere' }} variant="h3">
                    {sequenceDetailQuery.data.operations.join(' → ')}
                  </Typography>
                  <Chip label={`${sequenceDetailQuery.data.length} operations`} size="small" />
                </Stack>
              ) : (
                <EmptyState
                  action={
                    <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
                      <Button disabled={operationRows.length === 0} onClick={selectFirstRiskyOperation} size="small" variant="contained">
                        Select first risky operation
                      </Button>
                      <Button
                        disabled={edgeRows.length === 0}
                        onClick={() => {
                          if (edgeRows[0]) selectEdgeRow(edgeRows[0])
                        }}
                        size="small"
                        variant="outlined"
                      >
                        Open graph edge
                      </Button>
                      <Button
                        disabled={runBookmarks.length === 0}
                        onClick={() => document.getElementById('pinned-evidence-tray')?.scrollIntoView({ block: 'start' })}
                        size="small"
                        variant="outlined"
                      >
                        View pinned evidence
                      </Button>
                    </Stack>
                  }
                  description="Select an operation, edge, or sequence to inspect it here."
                  title="Nothing selected"
                />
              )}

              <Divider />
              <TextField
                fullWidth
                label="Local note"
                multiline
                onChange={(event) => setNoteDraft(event.target.value)}
                placeholder="Keep notes local. Avoid pasting secrets."
                rows={4}
                value={noteDraft || currentNote?.note || ''}
              />
              <Button disabled={!selected} onClick={saveSelectedNote} variant="outlined">
                Save note
              </Button>
              <Typography color="text.secondary" variant="caption">
                Notes and bookmarks stay in this browser unless explicitly included in a sanitized export.
              </Typography>
            </Stack>
          </Panel>
        </Grid>
      </Grid>

      <Panel
        id="pinned-evidence-tray"
        subtitle={`${runBookmarks.length} pinned entities · ${runRecentEntities.length} recent entities`}
        title="Pinned evidence and recent activity"
        {...tourAnchor(TOUR_ANCHORS.workspaceEvidenceTray)}
      >
        <Stack spacing={2}>
          {runBookmarks.length > 0 ? (
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              {runBookmarks.map((bookmark) => (
                <Button key={bookmark.id} href={bookmark.href} size="small" variant="outlined">
                  {bookmark.label}
                </Button>
              ))}
            </Stack>
          ) : (
            <Typography color="text.secondary" variant="body2">
              Bookmark operations, graph edges, or sequences to keep investigation context close.
            </Typography>
          )}
          {runRecentEntities.length > 0 ? (
            <Stack spacing={1}>
              <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
                Recent activity
              </Typography>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                {runRecentEntities.map((entity) => (
                  <Button key={`${entity.entityType}:${entity.entityId}`} href={entity.href} size="small" variant="text">
                    {entity.label}
                  </Button>
                ))}
              </Stack>
            </Stack>
          ) : null}
        </Stack>
      </Panel>

      <SavedViewDialog onClose={() => setSaveViewOpen(false)} onSave={saveCurrentView} open={saveViewOpen} />
      <ExportSnapshotDialog
        data={{
          edges: edgeRows,
          operations: operationRows,
          selectedEdge: edgeDetailQuery.data,
          selectedOperation,
          selectedSequence: sequenceDetailQuery.data,
        }}
        filters={search}
        localContext={{ bookmarks: runBookmarks, notes: runNotes }}
        localContextLabel="local notes and bookmarks"
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={currentRouteFallback(runName, search)}
        selectedContext={selectedOperation ?? edgeDetailQuery.data ?? sequenceDetailQuery.data}
        title="Workspace"
      />
    </Stack>
  )
}
