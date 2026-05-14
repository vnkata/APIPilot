import CloseIcon from '@mui/icons-material/Close'
import { useMemo } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Drawer,
  Grid,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  type Edge,
  type EdgeTypes,
  type Node,
  type NodeTypes,
} from 'reactflow'

import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { EmptyState } from '../../shared/ui/EmptyState'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import type { GraphEdgeResponse } from '../../shared/api/generated/model'
import { useAppDispatch, useAppSelector } from '../../app/hooks'
import {
  selectWorkspacePreferences,
  setGraphLayoutMode,
} from '../workspace-preferences/workspacePreferencesSlice'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { layoutGraph, type LayoutMode } from './layoutGraph'
import { useDependencyGraph, useGraphEdges, useOperations } from './api'
import { getGraphEdgeId } from './edgeIds'

export type GraphPageSearch = {
  edgeId?: string
  fromNode?: string
  groupBy?: string
  limit: number
  offset: number
  operationId?: string
  q?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  toNode?: string
}

type GraphPageProps = {
  runName: string
  search: GraphPageSearch
}

type EdgeRow = GraphEdgeResponse & {
  id: string
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

function EdgeDetailDrawer({ edge }: { edge?: EdgeRow }) {
  const open = Boolean(edge)

  function handleClose() {
    replaceSearchParams({ edgeId: undefined })
  }

  return (
    <Drawer
      anchor="right"
      onClose={handleClose}
      open={open}
      slotProps={{ paper: { sx: { maxWidth: '100%', width: { xs: '100%', sm: 520 } } } }}
      variant="persistent"
    >
      <Box aria-label="Edge detail" role="dialog" sx={{ height: '100%', overflow: 'auto', p: 2 }}>
        <Stack spacing={2}>
          <Stack direction="row" sx={{ alignItems: 'flex-start', gap: 1 }}>
            <Stack spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
              <Typography component="h2" variant="h3">
                Edge detail
              </Typography>
              <Typography color="text.secondary" noWrap variant="body2">
                {edge?.id}
              </Typography>
            </Stack>
            <IconButton aria-label="Close edge detail" onClick={handleClose} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Stack>

          {edge ? (
            <>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Chip label={`${edge.similar_parameters.length} evidence items`} />
                <Chip label={edge.from_node} variant="outlined" />
                <Chip label={edge.to_node} variant="outlined" />
              </Stack>
              <Divider />
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Button
                  onClick={() => replaceSearchParams({ edgeId: undefined, fromNode: edge.from_node, offset: 0 })}
                  size="small"
                  variant="outlined"
                >
                  Filter from
                </Button>
                <Button
                  onClick={() => replaceSearchParams({ edgeId: undefined, offset: 0, toNode: edge.to_node })}
                  size="small"
                  variant="outlined"
                >
                  Filter to
                </Button>
                <Button onClick={() => replaceSearchParams({ operationId: edge.from_node })} size="small">
                  Open source operation
                </Button>
                <Button onClick={() => replaceSearchParams({ operationId: edge.to_node })} size="small">
                  Open target operation
                </Button>
              </Stack>
              <Typography component="h3" variant="subtitle2">
                Similar parameters
              </Typography>
              <Stack spacing={1}>
                {edge.similar_parameters.map((item) => (
                  <Stack
                    key={`${item.value1}-${item.value2}-${item.in_value}`}
                    direction="row"
                    sx={{ flexWrap: 'wrap', gap: 1 }}
                  >
                    {item.value1 ? <Chip label={item.value1} variant="outlined" /> : null}
                    {item.value2 ? <Chip label={item.value2} variant="outlined" /> : null}
                    {item.in_value ? <Chip label={item.in_value} /> : null}
                  </Stack>
                ))}
              </Stack>
              <JsonBlock maxHeight={320} value={edge.similar_parameters} />
            </>
          ) : null}
        </Stack>
      </Box>
    </Drawer>
  )
}

export function GraphPage({ runName, search }: GraphPageProps) {
  const preferences = useAppSelector(selectWorkspacePreferences)
  const dispatch = useAppDispatch()
  const gridState = useUrlBackedGridState(search)
  const layoutMode = preferences.graphLayoutMode
  const selectedNodeId = search.operationId ?? null
  const graphQuery = useDependencyGraph(runName)
  const edgesQuery = useGraphEdges(runName, {
    from_node: search.fromNode,
    group_by: search.groupBy,
    limit: search.limit,
    offset: search.offset,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
    to_node: search.toNode,
    q: search.q,
  })
  const operationsQuery = useOperations(runName)

  const flow = useMemo(
    () =>
      buildFlow(
        graphQuery.data?.nodes ?? [],
        graphQuery.data?.edges ?? [],
        search.q,
        layoutMode,
      ),
    [graphQuery.data?.edges, graphQuery.data?.nodes, layoutMode, search.q],
  )

  const edgeRows: EdgeRow[] = (edgesQuery.data?.items ?? []).map((edge) => ({
    ...edge,
    id: getGraphEdgeId(edge),
  }))
  const selectedEdge = edgeRows.find((row) => row.id === search.edgeId)
  const selectedOutgoing = graphQuery.data?.edges.filter((edge) => edge.from_node === selectedNodeId) ?? []
  const selectedIncoming = graphQuery.data?.edges.filter((edge) => edge.to_node === selectedNodeId) ?? []
  const edgeColumns = useMemo<GridColDef<EdgeRow>[]>(
    () => [
      {
        field: 'from_node',
        flex: 1,
        headerName: 'From',
        minWidth: 180,
        renderCell: (params) => (
          <Button
            aria-label="Filter source node"
            onClick={(event) => {
              event.stopPropagation()
              replaceSearchParams({ edgeId: undefined, fromNode: params.row.from_node, offset: 0 })
            }}
            size="small"
          >
            {params.row.from_node}
          </Button>
        ),
      },
      {
        field: 'to_node',
        flex: 1,
        headerName: 'To',
        minWidth: 180,
        renderCell: (params) => (
          <Button
            aria-label="Filter target node"
            onClick={(event) => {
              event.stopPropagation()
              replaceSearchParams({ edgeId: undefined, offset: 0, toNode: params.row.to_node })
            }}
            size="small"
          >
            {params.row.to_node}
          </Button>
        ),
      },
      {
        field: 'similar_parameters',
        flex: 1.5,
        headerName: 'Evidence',
        minWidth: 240,
        valueGetter: (_value, row) =>
          row.similar_parameters
            .map((item) => [item.value1, item.value2].filter(Boolean).join(' -> '))
            .join(', '),
      },
    ],
    [],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        eyebrow="Dependency graph"
        title="Graph and operations"
        subtitle="Visualize operation dependencies inferred from APIPilot artifacts."
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
                      replaceSearchParams({ edgeId: undefined, offset: 0, q: event.target.value })
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
                      <Typography>{selectedNodeId}</Typography>
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
              <Typography component="h2" variant="h3">
                Graph edges
              </Typography>
              <FilterToolbar>
                <TextField
                  label="From node"
                  onChange={(event) => replaceSearchParams({ edgeId: undefined, fromNode: event.target.value, offset: 0 })}
                  size="small"
                  sx={{ minWidth: 220 }}
                  value={search.fromNode ?? ''}
                />
                <TextField
                  label="To node"
                  onChange={(event) => replaceSearchParams({ edgeId: undefined, offset: 0, toNode: event.target.value })}
                  size="small"
                  sx={{ minWidth: 220 }}
                  value={search.toNode ?? ''}
                />
                <TextField
                  label="Group"
                  onChange={(event) => replaceSearchParams({ edgeId: undefined, groupBy: event.target.value, offset: 0 })}
                  select
                  size="small"
                  sx={{ minWidth: 160 }}
                  value={search.groupBy ?? ''}
                >
                  <MenuItem value="">No grouping</MenuItem>
                  <MenuItem value="from_node">From node</MenuItem>
                  <MenuItem value="to_node">To node</MenuItem>
                </TextField>
              </FilterToolbar>
              <ActiveFilterChips
                filters={[
                  { key: 'q', label: 'Search', value: search.q },
                  { key: 'fromNode', label: 'From', value: search.fromNode },
                  { key: 'toNode', label: 'To', value: search.toNode },
                  { key: 'groupBy', label: 'Group', value: search.groupBy },
                  { key: 'edgeId', label: 'Edge', value: search.edgeId },
                ]}
              />
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
                  getRowId={(row) => row.id}
                  loading={edgesQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onRowClick={(params) => replaceSearchParams({ edgeId: params.row.id })}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={edgesQuery.data?.pagination.total ?? 0}
                  rows={edgeRows}
                  sortModel={gridState.sortModel}
                />
              </QueryState>
            </Stack>
          </CardContent>
        </Card>
        <EdgeDetailDrawer edge={selectedEdge} />
        <OperationDetailDrawer operationId={search.operationId} runName={runName} />
      </QueryState>
    </Stack>
  )
}
