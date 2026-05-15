import DownloadIcon from '@mui/icons-material/Download'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useMemo, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type EdgeTypes,
  type Node,
  type NodeTypes,
} from 'reactflow'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import type {
  GraphEdgeResponse,
  GraphExplorerEdgeResponse,
  GraphNodeResponse,
  GraphSequenceResponse,
  SortOrder,
} from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { EmptyState } from '../../shared/ui/EmptyState'
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
  selectWorkspacePreferences,
  setGraphLayoutMode,
} from '../workspace-preferences/workspacePreferencesSlice'
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
  useOperations,
} from './api'
import { getGraphEdgeId } from './edgeIds'
import { layoutGraph, type LayoutMode } from './layoutGraph'

export type GraphTab = 'edges' | 'nodes' | 'sequences' | 'visual'

export type GraphPageSearch = {
  edgeId?: string
  edgeStatus?: string
  evidenceSource?: string
  fromNode?: string
  fromOperationId?: string
  graphTab?: GraphTab
  groupBy?: string
  limit: number
  nodeKind?: string
  offset: number
  operationId?: string
  q?: string
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

const nodeTypes: NodeTypes = {}
const edgeTypes: EdgeTypes = {}

function buildFlow(nodes: string[], edges: GraphEdgeResponse[], q: string | undefined, mode: LayoutMode) {
  const normalizedQuery = q?.trim().toLowerCase()
  const filteredNodes = normalizedQuery
    ? nodes.filter((node) => node.toLowerCase().includes(normalizedQuery))
    : nodes
  const nodeSet = new Set(filteredNodes)
  const filteredEdges = edges.filter((edge) => {
    if (!normalizedQuery) return true
    return (
      edge.from_node.toLowerCase().includes(normalizedQuery) ||
      edge.to_node.toLowerCase().includes(normalizedQuery)
    )
  })

  filteredEdges.forEach((edge) => {
    nodeSet.add(edge.from_node)
    nodeSet.add(edge.to_node)
  })

  const flowNodes: Node[] = Array.from(nodeSet).map((node) => ({
    id: node,
    data: { label: node },
    position: { x: 0, y: 0 },
    style: {
      border: '1px solid #1f6feb',
      borderRadius: 8,
      fontSize: 12,
      padding: 8,
      width: 180,
    },
  }))

  const flowEdges: Edge[] = filteredEdges.map((edge) => ({
    id: getGraphEdgeId(edge),
    source: edge.from_node,
    target: edge.to_node,
    animated: true,
    label: edge.similar_parameters.length,
  }))

  return {
    edges: flowEdges,
    nodes: layoutGraph(flowNodes, flowEdges, mode),
  }
}

export function GraphPage({ runName, search }: GraphPageProps) {
  const [exportOpen, setExportOpen] = useState(false)
  const preferences = useAppSelector(selectWorkspacePreferences)
  const dispatch = useAppDispatch()
  const gridState = useUrlBackedGridState(search)
  const layoutMode = preferences.graphLayoutMode
  const selectedNodeId = search.operationId ?? null
  const tab = search.graphTab ?? 'edges'
  const graphQuery = useDependencyGraph(runName)
  const edgeParams = toGraphEdgeParams(search)
  const facetParams = toGraphFacetParams(search)
  const nodeParams = toGraphNodeParams(search)
  const sequenceParams = toGraphSequenceParams(search)
  const edgesQuery = useGraphEdges(runName, edgeParams)
  const facetsQuery = useGraphFacets(runName, facetParams)
  const nodesQuery = useGraphNodes(runName, nodeParams, { query: { enabled: tab === 'nodes' } })
  const sequencesQuery = useGraphSequences(runName, sequenceParams, { query: { enabled: tab === 'sequences' } })
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
  const operationsQuery = useOperations(runName)

  const flow = useMemo(
    () => buildFlow(graphQuery.data?.nodes ?? [], graphQuery.data?.edges ?? [], search.q, layoutMode),
    [graphQuery.data?.edges, graphQuery.data?.nodes, layoutMode, search.q],
  )
  const selectedOutgoing = graphQuery.data?.edges.filter((edge) => edge.from_node === selectedNodeId) ?? []
  const selectedIncoming = graphQuery.data?.edges.filter((edge) => edge.to_node === selectedNodeId) ?? []

  const edgeRows = edgesQuery.data?.items ?? []
  const nodeRows = nodesQuery.data?.items ?? []
  const sequenceRows = sequencesQuery.data?.items ?? []
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
          <Button onClick={() => setExportOpen(true)} startIcon={<DownloadIcon />} variant="outlined">
            Export snapshot
          </Button>
        }
        eyebrow="Dependency graph"
        subtitle="Visualize operation dependencies, edge evidence, nodes, and generated operation sequences."
        title="Graph and operations"
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
            <Card variant="outlined">
              <CardContent>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} sx={{ mb: 2 }}>
                  <TextField
                    fullWidth
                    label="Search graph"
                    onChange={(event) => {
                      replaceSearchParams({ edgeId: undefined, offset: 0, q: event.target.value, sequenceId: undefined })
                    }}
                    size="small"
                    value={search.q ?? ''}
                  />
                  <ToggleButtonGroup
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

                <Box sx={{ border: '1px solid', borderColor: 'divider', height: 460 }}>
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
                        replaceSearchParams({ operationId: node.id })
                      }}
                    >
                      <MiniMap pannable zoomable />
                      <Controls />
                      <Background />
                    </ReactFlow>
                  )}
                </Box>

                <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1, mt: 2 }}>
                  {(graphQuery.data?.nodes ?? []).map((node) => (
                    <Button
                      key={node}
                      onClick={() => {
                        replaceSearchParams({ operationId: node })
                      }}
                      size="small"
                      variant={selectedNodeId === node ? 'contained' : 'outlined'}
                    >
                      {node}
                    </Button>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, lg: 4 }}>
            <Card variant="outlined" sx={{ height: '100%' }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Typography component="h2" variant="h3">
                    Selected node
                  </Typography>
                  {selectedNodeId ? (
                    <>
                      <Typography sx={{ wordBreak: 'break-word' }}>{selectedNodeId}</Typography>
                      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                        <Chip label={`${selectedIncoming.length} incoming`} size="small" />
                        <Chip label={`${selectedOutgoing.length} outgoing`} size="small" />
                      </Stack>
                      <Button onClick={() => replaceSearchParams({ operationId: selectedNodeId })} size="small">
                        Open operation detail
                      </Button>
                    </>
                  ) : (
                    <Typography color="text.secondary" variant="body2">
                      Select a graph node to inspect operation detail.
                    </Typography>
                  )}
                  <Divider />
                  <Typography color="text.secondary" variant="body2">
                    Operations loaded: {operationsQuery.data?.operations.length ?? 0}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Card variant="outlined">
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
                  <Tab label="Visual" value="visual" />
                  <Tab label="Edges" value="edges" />
                  <Tab label="Nodes" value="nodes" />
                  <Tab label="Sequences" value="sequences" />
                </Tabs>
              </Stack>

              <FilterToolbar>
                <TextField
                  label="From operation"
                  onChange={(event) => replaceSearchParams({ edgeId: undefined, fromOperationId: event.target.value, offset: 0 })}
                  size="small"
                  sx={{ minWidth: 220 }}
                  value={search.fromOperationId ?? ''}
                />
                <TextField
                  label="To operation"
                  onChange={(event) => replaceSearchParams({ edgeId: undefined, offset: 0, toOperationId: event.target.value })}
                  size="small"
                  sx={{ minWidth: 220 }}
                  value={search.toOperationId ?? ''}
                />
                <TextField
                  label="Target operation"
                  onChange={(event) => replaceSearchParams({ offset: 0, sequenceId: undefined, targetOperationId: event.target.value })}
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
                  { key: 'sequenceId', label: 'Sequence', value: search.sequenceId },
                ]}
              />

              {tab === 'nodes' ? (
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
                    getRowId={(row) => row.node_id}
                    loading={nodesQuery.isFetching}
                    onPaginationModelChange={gridState.handlePaginationModelChange}
                    onSortModelChange={gridState.handleSortModelChange}
                    paginationModel={gridState.paginationModel}
                    rowCount={nodesQuery.data?.pagination.total ?? 0}
                    rows={nodeRows}
                    sortModel={gridState.sortModel}
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
                    getRowId={(row) => row.sequence_id}
                    loading={sequencesQuery.isFetching}
                    onPaginationModelChange={gridState.handlePaginationModelChange}
                    onRowClick={(params) => replaceSearchParams({ sequenceId: params.row.sequence_id })}
                    onSortModelChange={gridState.handleSortModelChange}
                    paginationModel={gridState.paginationModel}
                    rowCount={sequencesQuery.data?.pagination.total ?? 0}
                    rows={sequenceRows}
                    sortModel={gridState.sortModel}
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
                    getRowId={(row) => row.edge_id}
                    loading={edgesQuery.isFetching}
                    onPaginationModelChange={gridState.handlePaginationModelChange}
                    onRowClick={(params) => replaceSearchParams({ edgeId: params.row.edge_id })}
                    onSortModelChange={gridState.handleSortModelChange}
                    paginationModel={gridState.paginationModel}
                    rowCount={edgesQuery.data?.pagination.total ?? 0}
                    rows={edgeRows}
                    sortModel={gridState.sortModel}
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
          <Stack spacing={2}>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Chip label={edgeDetailQuery.data.edge_status} size="small" />
              <Chip label={`${edgeDetailQuery.data.evidence_count} evidence items`} size="small" variant="outlined" />
              {edgeDetailQuery.data.evidence_sources.map((source) => (
                <Chip key={source} label={source} size="small" variant="outlined" />
              ))}
            </Stack>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Button onClick={() => replaceSearchParams({ operationId: edgeDetailQuery.data?.from_operation_id })} size="small">
                Open source operation
              </Button>
              <Button onClick={() => replaceSearchParams({ operationId: edgeDetailQuery.data?.to_operation_id })} size="small">
                Open target operation
              </Button>
            </Stack>
            <JsonBlock maxHeight={360} value={edgeDetailQuery.data.evidence} />
          </Stack>
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
            <JsonBlock maxHeight={360} value={sequenceDetailQuery.data} />
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
