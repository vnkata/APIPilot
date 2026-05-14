import * as dagre from 'dagre'
import type { Edge, Node } from 'reactflow'

export type LayoutMode = 'dagre' | 'grid'

export function layoutGraph(nodes: Node[], edges: Edge[], mode: LayoutMode) {
  if (mode === 'grid') {
    return nodes.map((node, index) => ({
      ...node,
      position: {
        x: (index % 3) * 240,
        y: Math.floor(index / 3) * 140,
      },
    }))
  }

  const graph = new dagre.graphlib.Graph()
  graph.setDefaultEdgeLabel(() => ({}))
  graph.setGraph({ rankdir: 'LR', nodesep: 48, ranksep: 96 })

  nodes.forEach((node) => graph.setNode(node.id, { height: 56, width: 180 }))
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target))
  dagre.layout(graph)

  return nodes.map((node) => {
    const positioned = graph.node(node.id)
    return {
      ...node,
      position: {
        x: positioned.x - 90,
        y: positioned.y - 28,
      },
    }
  })
}
