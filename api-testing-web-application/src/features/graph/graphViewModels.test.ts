import { graph, graphEdges, graphSequences, operationExplorerEntries } from '../../test/fixtures'
import {
  buildGraphNavigatorModel,
  buildSpatialGraphData,
  findSelectedPathSequence,
  shouldAnimateGraph,
  summarizeGraphEdgeDetail,
} from './graphViewModels'

describe('graph view models', () => {
  it('respects explicit and system motion preferences', () => {
    expect(shouldAnimateGraph('auto', false)).toBe(true)
    expect(shouldAnimateGraph('auto', true)).toBe(false)
    expect(shouldAnimateGraph('reduced', false)).toBe(false)
    expect(shouldAnimateGraph('off', false)).toBe(false)
  })

  it('finds the visual path from selectedPath before sequenceId', () => {
    expect(findSelectedPathSequence(graphSequences.items, 'seq-create-list', undefined)?.sequence_id).toBe('seq-create-list')
    expect(findSelectedPathSequence(graphSequences.items, undefined, 'seq-create-list')?.sequence_id).toBe('seq-create-list')
  })

  it('filters navigator to selected node neighborhood', () => {
    const model = buildGraphNavigatorModel({
      edgeRows: graphEdges.items,
      edges: graph.edges,
      focusMode: 'neighborhood',
      layoutMode: 'dagre',
      motionEnabled: true,
      nodes: graph.nodes,
      operationRows: operationExplorerEntries.items,
      q: undefined,
      selectedNodeId: 'get-/items',
      selectedPathSequence: undefined,
    })

    expect(model.nodes.map((node) => node.id).sort()).toEqual(['get-/items', 'post-/items'])
    expect(model.edges).toHaveLength(1)
    expect(model.nodes.find((node) => node.id === 'get-/items')?.data.risk).toBe('danger')
  })

  it('filters navigator to selected path and marks path edges', () => {
    const model = buildGraphNavigatorModel({
      edgeRows: graphEdges.items,
      edges: graph.edges,
      focusMode: 'path',
      layoutMode: 'dagre',
      motionEnabled: true,
      nodes: graph.nodes,
      operationRows: operationExplorerEntries.items,
      q: undefined,
      selectedNodeId: undefined,
      selectedPathSequence: graphSequences.items[0],
    })

    expect(model.pathLabel).toBe('post-/items -> get-/items')
    expect(model.edges[0]?.data?.isPathEdge).toBe(true)
    expect(model.edges[0]?.animated).toBe(true)
  })

  it('builds spatial graph data from the same focused model', () => {
    const model = buildGraphNavigatorModel({
      edgeRows: graphEdges.items,
      edges: graph.edges,
      focusMode: 'all',
      layoutMode: 'dagre',
      motionEnabled: false,
      nodes: graph.nodes,
      operationRows: operationExplorerEntries.items,
      q: undefined,
      selectedNodeId: 'get-/items',
      selectedPathSequence: graphSequences.items[0],
    })

    const spatial = buildSpatialGraphData(model)

    expect(spatial.nodes).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ id: 'get-/items', risk: 'danger' }),
        expect.objectContaining({ id: 'post-/items' }),
      ]),
    )
    expect(spatial.links[0]).toMatchObject({ isPathLink: true, value: 1 })
  })

  it('does not mark raw invariant rows alone as graph warning risk', () => {
    const model = buildGraphNavigatorModel({
      edgeRows: graphEdges.items,
      edges: graph.edges,
      focusMode: 'all',
      layoutMode: 'dagre',
      motionEnabled: false,
      nodes: graph.nodes,
      operationRows: operationExplorerEntries.items.map((operation) => (
        operation.operation_id === 'post-/items'
          ? { ...operation, constraint_count: 0, invariant_count: 4 }
          : operation
      )),
      q: undefined,
      selectedNodeId: undefined,
      selectedPathSequence: undefined,
    })

    expect(model.nodes.find((node) => node.id === 'post-/items')?.data.risk).toBe('success')
  })

  it('summarizes edge evidence without requiring raw JSON', () => {
    expect(
      summarizeGraphEdgeDetail({
        ...graphEdges.items[0],
        evidence: [
          {
            evidence_id: 'ev-1',
            relation_hint: 'response to parameter via test',
            source: 'final_graph',
            source_artifact_id: 'dependency_graph',
            value1: 'item.id',
            value2: 'itemId',
          },
        ],
      }),
    ).toMatchObject({
      evidenceItems: [
        expect.objectContaining({
          label: 'item.id -> itemId',
          source: 'final_graph',
        }),
      ],
      routeLabel: 'post-/items -> get-/items',
    })
  })
})
