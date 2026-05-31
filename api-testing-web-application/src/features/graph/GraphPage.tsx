import DownloadIcon from '@mui/icons-material/Download'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { lazy, Suspense, useMemo, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type EdgeTypes,
  type NodeTypes,
} from 'reactflow'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import type {
  GraphExplorerEdgeResponse,
  GraphNodeResponse,
  GraphSequenceResponse,
  SortOrder,
} from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { useGraphSearchActions } from '../../shared/lib/searchActions'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { DebouncedTextField } from '../../shared/ui/DebouncedTextField'
import { EmptyState } from '../../shared/ui/EmptyState'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FacetFilterBar, type FacetFilter } from '../../shared/ui/FacetFilterBar'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { GuidanceCallout } from '../../shared/ui/Guidance'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { RawFieldsAccordion } from '../../shared/ui/RawFieldsAccordion'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { ViewModeToggle } from '../../shared/ui/ViewModeToggle'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
import {
  selectWorkspacePreferences,
  setGraphLayoutMode,
} from '../workspace-preferences/workspacePreferencesSlice'
import { useOperationExplorerEntries } from '../operations/api'
import {
  toGraphEdgeParams,
  toGraphFacetParams,
  toGraphNodeParams,
  toGraphSequenceParams,
  useDependencyGraph,
  useGraphEdgeDetail,
  useGraphEdges,
  useGraphFacets,
  useGraphNodes,
  useGraphSequenceDetail,
  useGraphSequences,
} from './api'
import { EvidenceGraphEdge, OperationGraphNode } from './GraphNavigatorComponents'
import { DependencyJourneyView, GraphInspectorPanel, VisualGraphList } from './GraphExplorerPanels'
import {
  buildGraphNavigatorModel,
  buildSpatialGraphData,
  findSelectedPathSequence,
  shouldAnimateGraph,
  summarizeGraphEdgeDetail,
  type FocusMode,
  type MotionMode,
} from './graphViewModels'
import type { LayoutMode } from './layoutGraph'

const SpatialGraph3D = lazy(() =>
  import('./SpatialGraph3D').then((module) => ({ default: module.SpatialGraph3D })),
)

export type GraphTab = 'edges' | 'nodes' | 'sequences' | 'visual'

export type GraphPageSearch = {
  edgeId?: string
  edgeStatus?: string
  evidenceSource?: string
  focusMode?: FocusMode
  fromNode?: string
  fromOperationId?: string
  graphTab?: GraphTab
  graphView?: 'explorer' | 'journey' | 'spatial'
  groupBy?: string
  limit: number
  motionMode?: MotionMode
  nodeKind?: string
  offset: number
  operationId?: string
  q?: string
  selectedPath?: string
  sequenceId?: string
  sequenceType?: string
  sortBy?: string
  sortOrder?: SortOrder
  targetOperationId?: string
  toNode?: string
  toOperationId?: string
}

type GraphPageProps = {
  runName: string
  search: GraphPageSearch
}

const nodeTypes: NodeTypes = { operationNode: OperationGraphNode }
const edgeTypes: EdgeTypes = { evidenceEdge: EvidenceGraphEdge }

export function GraphPage({ runName, search }: GraphPageProps) {
  const [exportOpen, setExportOpen] = useState(false)
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const isDesktop = useMediaQuery('(min-width:900px)')
  const preferences = useAppSelector(selectWorkspacePreferences)
  const dispatch = useAppDispatch()
  const graphSearchActions = useGraphSearchActions()
  const gridState = useUrlBackedGridState(search)
  const encodedRunName = encodeRoutePart(runName)
  const layoutMode = preferences.graphLayoutMode
  const selectedNodeId = search.operationId ?? null
  const tab = search.graphTab ?? 'edges'
  const graphView = search.graphView ?? 'explorer'
  const focusMode = search.focusMode ?? 'all'
  const motionMode = search.motionMode ?? 'auto'
  const motionEnabled = shouldAnimateGraph(motionMode, prefersReducedMotion)
  const graphQuery = useDependencyGraph(runName)
  const edgeParams = toGraphEdgeParams(search)
  const facetParams = toGraphFacetParams(search)
  const nodeParams = toGraphNodeParams(search)
  const sequenceParams = toGraphSequenceParams(search)
  const edgesQuery = useGraphEdges(runName, edgeParams)
  const facetsQuery = useGraphFacets(runName, facetParams)
  const nodesQuery = useGraphNodes(runName, nodeParams, { query: { enabled: tab === 'nodes' } })
  const sequencesQuery = useGraphSequences(runName, sequenceParams, {
    query: {
      enabled: graphView === 'journey' || graphView === 'spatial' || tab === 'sequences' || Boolean(search.selectedPath),
    },
  })
  const edgeDetailOpen = Boolean(search.edgeId)
  const edgeDetailQuery = useGraphEdgeDetail(
    runName,
    search.edgeId ?? '',
    { query: { enabled: edgeDetailOpen } },
  )
  const sequenceDetailOpen = Boolean(search.sequenceId)
  const sequenceDetailQuery = useGraphSequenceDetail(
    runName,
    search.sequenceId ?? '',
    { query: { enabled: sequenceDetailOpen } },
  )
  const operationEntriesQuery = useOperationExplorerEntries(
    runName,
    { limit: Math.min(search.limit, 50), offset: 0, q: search.q },
    { query: { enabled: graphView === 'spatial' || tab === 'visual' || focusMode !== 'all' } },
  )
  const operationRows = useMemo(
    () => operationEntriesQuery.data?.items ?? [],
    [operationEntriesQuery.data?.items],
  )
  const edgeRows = useMemo(
    () => edgesQuery.data?.items ?? [],
    [edgesQuery.data?.items],
  )
  const nodeRows = nodesQuery.data?.items ?? []
  const sequenceRows = sequencesQuery.data?.items ?? []
  const selectedPathSequence = findSelectedPathSequence(sequenceRows, search.selectedPath, search.sequenceId)

  const flow = useMemo(
    () =>
      buildGraphNavigatorModel({
        edgeRows,
        edges: graphQuery.data?.edges ?? [],
        focusMode,
        layoutMode,
        motionEnabled,
        nodes: graphQuery.data?.nodes ?? [],
        operationRows,
        q: search.q,
        selectedNodeId,
        selectedPathSequence,
      }),
    [
      edgeRows,
      focusMode,
      graphQuery.data?.edges,
      graphQuery.data?.nodes,
      layoutMode,
      motionEnabled,
      operationRows,
      search.q,
      selectedNodeId,
      selectedPathSequence,
    ],
  )
  const spatialGraph = useMemo(() => buildSpatialGraphData(flow), [flow])
  const selectedOutgoing = flow.edges.filter((edge) => edge.source === selectedNodeId)
  const selectedIncoming = flow.edges.filter((edge) => edge.target === selectedNodeId)
  const activeRows =
    tab === 'nodes' ? nodeRows : tab === 'sequences' ? sequenceRows : edgeRows

  const edgeColumns = useMemo<GridColDef<GraphExplorerEdgeResponse>[]>(
    () => [
      {
        field: 'from_operation_id',
        flex: 1,
        headerName: 'From operation',
        minWidth: 180,
        renderCell: (params) => (
          <Button
            onClick={(event) => {
              event.stopPropagation()
              replaceSearchParams({ edgeId: undefined, fromOperationId: params.row.from_operation_id, offset: 0 })
            }}
            size="small"
          >
            {params.row.from_operation_id}
          </Button>
        ),
      },
      {
        field: 'to_operation_id',
        flex: 1,
        headerName: 'To operation',
        minWidth: 180,
        renderCell: (params) => (
          <Button
            onClick={(event) => {
              event.stopPropagation()
              replaceSearchParams({ edgeId: undefined, offset: 0, toOperationId: params.row.to_operation_id })
            }}
            size="small"
          >
            {params.row.to_operation_id}
          </Button>
        ),
      },
      { field: 'edge_status', headerName: 'Status', minWidth: 120 },
      { field: 'evidence_count', headerName: 'Evidence', minWidth: 120 },
      {
        field: 'evidence_preview',
        flex: 1.5,
        headerName: 'Preview',
        minWidth: 240,
        valueGetter: (_value, row) => row.evidence_preview.join(', '),
      },
    ],
    [],
  )
  const nodeColumns = useMemo<GridColDef<GraphNodeResponse>[]>(
    () => [
      { field: 'node_kind', headerName: 'Kind', minWidth: 120 },
      { field: 'label', flex: 1, headerName: 'Label', minWidth: 180 },
      {
        field: 'operation_id',
        flex: 1,
        headerName: 'Operation',
        minWidth: 180,
        renderCell: (params) => (
          <Button onClick={() => replaceSearchParams({ operationId: params.row.operation_id })} size="small">
            {params.row.operation_id}
          </Button>
        ),
      },
      { field: 'in_degree', headerName: 'In', minWidth: 80 },
      { field: 'out_degree', headerName: 'Out', minWidth: 80 },
    ],
    [],
  )
  const sequenceColumns = useMemo<GridColDef<GraphSequenceResponse>[]>(
    () => [
      { field: 'sequence_id', flex: 1, headerName: 'Sequence', minWidth: 180 },
      { field: 'sequence_type', headerName: 'Type', minWidth: 180 },
      { field: 'target_operation_id', flex: 1, headerName: 'Target operation', minWidth: 180 },
      { field: 'length', headerName: 'Length', minWidth: 100 },
      { field: 'score', headerName: 'Score', minWidth: 100 },
    ],
    [],
  )

  const facets = facetsQuery.data
  const facetFilters: FacetFilter[] = [
    {
      buckets: facets?.edge_status,
      label: 'Edge status',
      onSelect: (value) => replaceSearchParams({ edgeStatus: value, offset: 0 }),
      selectedValue: search.edgeStatus,
    },
    {
      buckets: facets?.evidence_source,
      label: 'Evidence source',
      onSelect: (value) => replaceSearchParams({ evidenceSource: value, offset: 0 }),
      selectedValue: search.evidenceSource,
    },
    {
      buckets: facets?.node_kind,
      label: 'Node kind',
      onSelect: (value) => replaceSearchParams({ nodeKind: value, offset: 0 }),
      selectedValue: search.nodeKind,
    },
    {
      buckets: facets?.sequence_type,
      label: 'Sequence type',
      onSelect: (value) => replaceSearchParams({ sequenceType: value, offset: 0 }),
      selectedValue: search.sequenceType,
    },
  ]

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
            <ViewModeToggle
              ariaLabel="Graph view mode"
              onChange={(value) => replaceSearchParams({ graphView: value })}
              options={[
                { description: 'Navigator graph and explorer tables.', label: 'Explorer', value: 'explorer' },
                { description: 'Sequence-first dependency journey.', label: 'Journey', value: 'journey' },
                { description: 'Experimental desktop 3D dependency graph.', label: 'Spatial', value: 'spatial' },
              ]}
              value={graphView}
            />
            <Button onClick={() => setExportOpen(true)} startIcon={<DownloadIcon />} variant="outlined">
              Export snapshot
            </Button>
          </Stack>
        }
        eyebrow="Dependency graph"
        subtitle="Visualize operation dependencies, edge evidence, nodes, and generated operation sequences."
        title="Graph and operations"
        {...tourAnchor(TOUR_ANCHORS.graphHeader)}
      />

      <GuidanceCallout
        bullets={[
          'Explorer is the safest first stop for exact edge evidence.',
          'Journey is keyboard-friendly when Spatial looks sparse or inactive.',
          'Spatial is lazy-loaded and best for desktop visual scanning.',
        ]}
        title="Graph lens guide"
      />

      <QueryState
        empty={(graphQuery.data?.nodes.length ?? 0) === 0}
        emptyDescription="The dependency graph artifact is empty or unavailable."
        error={graphQuery.error}
        isError={graphQuery.isError}
        isLoading={graphQuery.isLoading}
        onRetry={() => void graphQuery.refetch()}
      >
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 8 }}>
            <Card variant="outlined" {...tourAnchor(TOUR_ANCHORS.graphControls)}>
              <CardContent>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} sx={{ mb: 2 }}>
                  <DebouncedTextField
                    fullWidth
                    label="Search graph"
                    onDebouncedChange={(value) => {
                      replaceSearchParams({ edgeId: undefined, offset: 0, q: value, sequenceId: undefined })
                    }}
                    size="small"
                    value={search.q ?? ''}
                  />
                  <ToggleButtonGroup
                    aria-label="Graph focus mode"
                    exclusive
                    onChange={(_, value: FocusMode | null) => {
                      if (value) replaceSearchParams({ focusMode: value, offset: 0 })
                    }}
                    size="small"
                    value={focusMode}
                  >
                    <ToggleButton value="all">All</ToggleButton>
                    <ToggleButton value="neighborhood">Neighborhood</ToggleButton>
                    <ToggleButton value="path">Path</ToggleButton>
                  </ToggleButtonGroup>
                  <ToggleButtonGroup
                    aria-label="Graph motion mode"
                    exclusive
                    onChange={(_, value: MotionMode | null) => {
                      if (value) replaceSearchParams({ motionMode: value })
                    }}
                    size="small"
                    value={motionMode}
                  >
                    <ToggleButton value="auto">Motion auto</ToggleButton>
                    <ToggleButton value="reduced">Reduced</ToggleButton>
                    <ToggleButton value="off">Off</ToggleButton>
                  </ToggleButtonGroup>
                  <ToggleButtonGroup
                    aria-label="Graph layout mode"
                    exclusive
                    onChange={(_, value: LayoutMode | null) => {
                      if (value) dispatch(setGraphLayoutMode(value))
                    }}
                    size="small"
                    value={layoutMode}
                  >
                    <ToggleButton value="dagre">Dagre</ToggleButton>
                    <ToggleButton value="grid">Grid</ToggleButton>
                  </ToggleButtonGroup>
                </Stack>
                <Stack
                  aria-label="Graph legend"
                  direction="row"
                  sx={{ flexWrap: 'wrap', gap: 1, mb: 2 }}
                >
                  <Chip label="Legend" size="small" />
                  <Chip label="final: high-confidence dependency" size="small" variant="outlined" />
                  <Chip label="candidate: lower-confidence evidence" size="small" variant="outlined" />
                  <Chip label={`Focus lens: ${focusMode}`} size="small" variant="outlined" />
                </Stack>

                {graphView === 'spatial' ? (
                  isDesktop ? (
                    <Stack spacing={2}>
                      <Box aria-label="Spatial graph status" role="region">
                        <Stack spacing={1.5}>
                          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ alignItems: { md: 'center' } }}>
                            <Typography component="h2" sx={{ flex: 1 }} variant="h3">
                              Spatial dependency graph
                            </Typography>
                            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                              <Chip label={`${spatialGraph.nodes.length} nodes`} size="small" />
                              <Chip label={`${spatialGraph.links.length} links`} size="small" variant="outlined" />
                              <Chip label={`Selected: ${selectedNodeId ?? search.selectedPath ?? 'none'}`} size="small" variant="outlined" />
                              <Chip label={`Motion: ${motionEnabled ? 'on' : 'off'}`} size="small" variant="outlined" />
                            </Stack>
                          </Stack>
                          <Typography color="text.secondary" variant="body2">
                            Viewport ready. Use Journey or Navigator when you need a keyboard-first evidence path, or reset selection to return to the full dependency map.
                          </Typography>
                          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                            <Button onClick={() => replaceSearchParams({ graphTab: 'sequences', graphView: 'journey' })} size="small" variant="outlined">
                              Open Journey
                            </Button>
                            <Button onClick={() => replaceSearchParams({ graphTab: 'visual', graphView: 'explorer' })} size="small" variant="outlined">
                              Open Navigator list
                            </Button>
                            <Button
                              onClick={() => replaceSearchParams({
                                edgeId: undefined,
                                operationId: undefined,
                                selectedPath: undefined,
                                sequenceId: undefined,
                              })}
                              size="small"
                              variant="outlined"
                            >
                              Reset selection
                            </Button>
                          </Stack>
                        </Stack>
                      </Box>
                      <Suspense fallback={<EmptyState title="Loading spatial graph" />}>
                        <SpatialGraph3D
                          data={spatialGraph}
                          motionEnabled={motionEnabled}
                          onNodeSelect={(operationId) => replaceSearchParams({ operationId })}
                        />
                      </Suspense>
                    </Stack>
                  ) : (
                    <Alert severity="info" variant="outlined">
                      <Stack spacing={1}>
                        <Typography variant="body2">
                          Spatial 3D is optimized for desktop. Mobile keeps the Navigator and Journey views for focused triage.
                        </Typography>
                        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                          <Button onClick={() => replaceSearchParams({ graphView: 'explorer' })} size="small" variant="outlined">
                            Open Explorer
                          </Button>
                          <Button onClick={() => replaceSearchParams({ graphView: 'journey' })} size="small" variant="outlined">
                            Open Journey
                          </Button>
                        </Stack>
                      </Stack>
                    </Alert>
                  )
                ) : null}

                {graphView !== 'spatial' || !isDesktop ? (
                  <>
                    <Box sx={{ border: '1px solid', borderColor: 'divider', height: 500 }}>
                      {flow.nodes.length === 0 ? (
                        <EmptyState title="No matching graph nodes" />
                      ) : (
                        <ReactFlow
                          edgeTypes={edgeTypes}
                          edges={flow.edges}
                          fitView
                          nodeTypes={nodeTypes}
                          nodes={flow.nodes}
                          onNodeClick={(_, node) => {
                            graphSearchActions.selectOperation(node.id)
                          }}
                        >
                          <MiniMap pannable zoomable />
                          <Controls />
                          <Background />
                        </ReactFlow>
                      )}
                    </Box>

                    <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, mt: 2 }}>
                      {flow.nodes.slice(0, 12).map((node) => (
                        <Button
                          key={node.id}
                          onClick={() => {
                            graphSearchActions.selectOperation(node.id)
                          }}
                          size="small"
                          variant={selectedNodeId === node.id ? 'contained' : 'outlined'}
                        >
                          {node.id}
                        </Button>
                      ))}
                    </Stack>
                  </>
                ) : null}
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, lg: 4 }} {...tourAnchor(TOUR_ANCHORS.graphInspector)}>
            <GraphInspectorPanel
              encodedRunName={encodedRunName}
              pathLabel={flow.pathLabel}
              selectedIncoming={selectedIncoming.length}
              selectedNodeId={selectedNodeId}
              selectedOutgoing={selectedOutgoing.length}
            />
          </Grid>
        </Grid>

        {graphView === 'journey' ? (
          <DependencyJourneyView edgeRows={edgeRows} sequenceRows={sequenceRows} />
        ) : null}

        <Card variant="outlined" {...tourAnchor(TOUR_ANCHORS.graphResults)}>
          <CardContent>
            <Stack spacing={2}>
              <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' } }}>
                <Typography component="h2" sx={{ flex: 1 }} variant="h3">
                  Graph explorer
                </Typography>
                <Tabs
                  onChange={(_, value: GraphTab) => {
                    replaceSearchParams({ edgeId: undefined, graphTab: value, offset: 0, sequenceId: undefined })
                  }}
                  value={tab}
                >
                  <Tab label="Navigator" value="visual" />
                  <Tab label="Edges" value="edges" />
                  <Tab label="Nodes" value="nodes" />
                  <Tab label="Sequences" value="sequences" />
                </Tabs>
              </Stack>

              <FilterToolbar>
                <DebouncedTextField
                  label="From operation"
                  onDebouncedChange={(value) => replaceSearchParams({ edgeId: undefined, fromOperationId: value, offset: 0 })}
                  size="small"
                  sx={{ minWidth: 220 }}
                  value={search.fromOperationId ?? ''}
                />
                <DebouncedTextField
                  label="To operation"
                  onDebouncedChange={(value) => replaceSearchParams({ edgeId: undefined, offset: 0, toOperationId: value })}
                  size="small"
                  sx={{ minWidth: 220 }}
                  value={search.toOperationId ?? ''}
                />
                <DebouncedTextField
                  label="Target operation"
                  onDebouncedChange={(value) => replaceSearchParams({ offset: 0, sequenceId: undefined, targetOperationId: value })}
                  size="small"
                  sx={{ minWidth: 220 }}
                  value={search.targetOperationId ?? ''}
                />
                <TextField
                  label="Group"
                  onChange={(event) => replaceSearchParams({ edgeId: undefined, groupBy: event.target.value, offset: 0, sequenceId: undefined })}
                  select
                  size="small"
                  sx={{ minWidth: 160 }}
                  value={search.groupBy ?? ''}
                >
                  <MenuItem value="">No grouping</MenuItem>
                  <MenuItem value="from_node">From node</MenuItem>
                  <MenuItem value="to_node">To node</MenuItem>
                  <MenuItem value="from_operation_id">From operation</MenuItem>
                  <MenuItem value="to_operation_id">To operation</MenuItem>
                  <MenuItem value="node_kind">Node kind</MenuItem>
                  <MenuItem value="sequence_type">Sequence type</MenuItem>
                </TextField>
              </FilterToolbar>

              <FacetFilterBar filters={facetFilters} />

              <ActiveFilterChips
                filters={[
                  { key: 'q', label: 'Search', value: search.q },
                  { key: 'focusMode', label: 'Focus', value: search.focusMode },
                  { key: 'motionMode', label: 'Motion', value: search.motionMode },
                  { key: 'fromNode', label: 'From node', value: search.fromNode },
                  { key: 'toNode', label: 'To node', value: search.toNode },
                  { key: 'fromOperationId', label: 'From operation', value: search.fromOperationId },
                  { key: 'toOperationId', label: 'To operation', value: search.toOperationId },
                  { key: 'edgeStatus', label: 'Edge status', value: search.edgeStatus },
                  { key: 'evidenceSource', label: 'Evidence source', value: search.evidenceSource },
                  { key: 'nodeKind', label: 'Node kind', value: search.nodeKind },
                  { key: 'sequenceType', label: 'Sequence type', value: search.sequenceType },
                  { key: 'targetOperationId', label: 'Target operation', value: search.targetOperationId },
                  { key: 'groupBy', label: 'Group', value: search.groupBy },
                  { key: 'edgeId', label: 'Edge', value: search.edgeId },
                  { key: 'selectedPath', label: 'Selected path', value: search.selectedPath },
                  { key: 'sequenceId', label: 'Sequence', value: search.sequenceId },
                ]}
              />

              {tab === 'visual' ? (
                <QueryState
                  empty={edgeRows.length === 0}
                  error={edgesQuery.error}
                  isError={edgesQuery.isError}
                  isLoading={edgesQuery.isLoading}
                  onRetry={() => void edgesQuery.refetch()}
                >
                  <VisualGraphList edgeRows={edgeRows} />
                </QueryState>
              ) : tab === 'nodes' ? (
                <QueryState
                  empty={nodeRows.length === 0}
                  error={nodesQuery.error}
                  isError={nodesQuery.isError}
                  isLoading={nodesQuery.isLoading}
                  onRetry={() => void nodesQuery.refetch()}
                >
                  <ServerDataGridPanel
                    ariaLabel="graph nodes"
                    columns={nodeColumns}
                    copyCellOnDoubleClick
                    getRowId={(row) => row.node_id}
                    loading={nodesQuery.isFetching}
                    onPaginationModelChange={gridState.handlePaginationModelChange}
                    onSortModelChange={gridState.handleSortModelChange}
                    paginationModel={gridState.paginationModel}
                    rowCount={nodesQuery.data?.pagination.total ?? 0}
                    rows={nodeRows}
                    sortModel={gridState.sortModel}
                    tableLayout={{ page: 'graph', runName, tableId: 'nodes' }}
                  />
                </QueryState>
              ) : tab === 'sequences' ? (
                <QueryState
                  empty={sequenceRows.length === 0}
                  error={sequencesQuery.error}
                  isError={sequencesQuery.isError}
                  isLoading={sequencesQuery.isLoading}
                  onRetry={() => void sequencesQuery.refetch()}
                >
                  <ServerDataGridPanel
                    ariaLabel="graph sequences"
                    columns={sequenceColumns}
                    copyCellOnDoubleClick
                    getRowId={(row) => row.sequence_id}
                    loading={sequencesQuery.isFetching}
                    onPaginationModelChange={gridState.handlePaginationModelChange}
                    onRowClick={(params) => replaceSearchParams({
                      selectedPath: params.row.sequence_id,
                      sequenceId: params.row.sequence_id,
                    })}
                    onSortModelChange={gridState.handleSortModelChange}
                    paginationModel={gridState.paginationModel}
                    rowCount={sequencesQuery.data?.pagination.total ?? 0}
                    rows={sequenceRows}
                    sortModel={gridState.sortModel}
                    tableLayout={{ page: 'graph', runName, tableId: 'sequences' }}
                  />
                </QueryState>
              ) : (
                <QueryState
                  empty={edgeRows.length === 0}
                  error={edgesQuery.error}
                  isError={edgesQuery.isError}
                  isLoading={edgesQuery.isLoading}
                  onRetry={() => void edgesQuery.refetch()}
                >
                  <ServerDataGridPanel
                    ariaLabel="graph edges"
                    columns={edgeColumns}
                    copyCellOnDoubleClick
                    getRowId={(row) => row.edge_id}
                    loading={edgesQuery.isFetching}
                    onPaginationModelChange={gridState.handlePaginationModelChange}
                    onRowClick={(params) => replaceSearchParams({ edgeId: params.row.edge_id })}
                    onSortModelChange={gridState.handleSortModelChange}
                    paginationModel={gridState.paginationModel}
                    rowCount={edgesQuery.data?.pagination.total ?? 0}
                    rows={edgeRows}
                    sortModel={gridState.sortModel}
                    tableLayout={{ page: 'graph', runName, tableId: 'edges' }}
                  />
                </QueryState>
              )}
            </Stack>
          </CardContent>
        </Card>
      </QueryState>

      <InvestigationDrawer
        ariaLabel="Edge detail"
        error={edgeDetailQuery.error}
        isError={edgeDetailQuery.isError}
        isLoading={edgeDetailQuery.isLoading}
        onClose={() => replaceSearchParams({ edgeId: undefined })}
        onRetry={() => void edgeDetailQuery.refetch()}
        open={edgeDetailOpen}
        subtitle={search.edgeId}
        title="Edge detail"
      >
        {edgeDetailQuery.data ? (
          (() => {
            const summary = summarizeGraphEdgeDetail(edgeDetailQuery.data)
            return (
              <Stack spacing={2}>
                <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                  <Chip label={edgeDetailQuery.data.edge_status} size="small" />
                  <Chip label={`${edgeDetailQuery.data.evidence_count} evidence items`} size="small" variant="outlined" />
                  {edgeDetailQuery.data.evidence_sources.map((source) => (
                    <Chip key={source} label={source} size="small" variant="outlined" />
                  ))}
                </Stack>
                <Typography component="h3" variant="h3">
                  {summary.routeLabel}
                </Typography>
                <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                  <Button onClick={() => replaceSearchParams({ operationId: edgeDetailQuery.data?.from_operation_id })} size="small">
                    Open source operation
                  </Button>
                  <Button onClick={() => replaceSearchParams({ operationId: edgeDetailQuery.data?.to_operation_id })} size="small">
                    Open target operation
                  </Button>
                </Stack>
                <Stack spacing={1}>
                  <Typography component="h4" variant="subtitle2">
                    Evidence summary
                  </Typography>
                  {summary.evidenceItems.map((item) => (
                    <Card key={`${item.source}-${item.label}`} variant="outlined">
                      <CardContent>
                        <Stack spacing={0.75}>
                          <Typography sx={{ overflowWrap: 'anywhere' }} variant="body2">
                            {item.label}
                          </Typography>
                          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                            <Chip label={item.relation} size="small" variant="outlined" />
                            <Chip label={item.source} size="small" variant="outlined" />
                          </Stack>
                        </Stack>
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
                <RawFieldsAccordion value={edgeDetailQuery.data.evidence} />
              </Stack>
            )
          })()
        ) : null}
      </InvestigationDrawer>

      <InvestigationDrawer
        ariaLabel="Sequence detail"
        error={sequenceDetailQuery.error}
        isError={sequenceDetailQuery.isError}
        isLoading={sequenceDetailQuery.isLoading}
        onClose={() => replaceSearchParams({ sequenceId: undefined })}
        onRetry={() => void sequenceDetailQuery.refetch()}
        open={sequenceDetailOpen}
        subtitle={search.sequenceId}
        title="Sequence detail"
      >
        {sequenceDetailQuery.data ? (
          <Stack spacing={2}>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip label={sequenceDetailQuery.data.sequence_type} size="small" />
              <Chip label={`${sequenceDetailQuery.data.length} operations`} size="small" variant="outlined" />
              {sequenceDetailQuery.data.score !== null && sequenceDetailQuery.data.score !== undefined ? (
                <Chip label={`score ${sequenceDetailQuery.data.score}`} size="small" variant="outlined" />
              ) : null}
            </Stack>
            <Typography component="h3" variant="h3">
              {sequenceDetailQuery.data.operations.join(' -> ')}
            </Typography>
            <Stack spacing={1}>
              <Typography component="h4" variant="subtitle2">
                Operation path
              </Typography>
              {sequenceDetailQuery.data.operations.map((operation, index) => (
                <Stack key={`${operation}-${index}`} direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                  <Chip label={index + 1} size="small" />
                  <Button onClick={() => replaceSearchParams({ operationId: operation })} size="small">
                    {operation}
                  </Button>
                </Stack>
              ))}
            </Stack>
            {sequenceDetailQuery.data.parameter_sources.length > 0 ? (
              <Stack spacing={1}>
                <Typography component="h4" variant="subtitle2">
                  Parameter sources
                </Typography>
                {sequenceDetailQuery.data.parameter_sources.map((source) => (
                    <Card key={`${source.source_operation_id ?? 'source'}-${source.parameter_name}`} variant="outlined">
                      <CardContent>
                        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                          <Chip label={source.parameter_name} size="small" />
                        <Chip label={source.source_operation_id ?? 'unknown source'} size="small" variant="outlined" />
                        <Chip label={source.source_property_path ?? 'unknown path'} size="small" variant="outlined" />
                      </Stack>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ) : null}
            <RawFieldsAccordion value={sequenceDetailQuery.data} />
          </Stack>
        ) : null}
      </InvestigationDrawer>

      <OperationDetailDrawer operationId={search.operationId} runName={runName} />

      <ExportSnapshotDialog
        data={activeRows}
        filters={search}
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={`/runs/${encodeRoutePart(runName)}/graph`}
        selectedContext={edgeDetailQuery.data ?? sequenceDetailQuery.data}
        title="Graph"
      />
    </Stack>
  )
}
