import type { Edge, Node } from 'reactflow'

import type {
  GraphEdgeDetailResponse,
  GraphEdgeResponse,
  GraphEvidenceResponse,
  GraphExplorerEdgeResponse,
  GraphSequenceResponse,
  OperationExplorerEntryResponse,
} from '../../shared/api/generated/model'
import { getGraphEdgeId } from './edgeIds'
import { layoutGraph, type LayoutMode } from './layoutGraph'

export type FocusMode = 'all' | 'neighborhood' | 'path'
export type MotionMode = 'auto' | 'off' | 'reduced'
export type GraphNodeRisk = 'danger' | 'neutral' | 'success' | 'warning'

export type NavigatorNodeData = {
  degreeLabel: string
  isPathNode: boolean
  isSelected: boolean
  label: string
  operationId: string
  risk: GraphNodeRisk
  statusLabel: string
}

export type NavigatorEdgeData = {
  evidenceCount: number
  isPathEdge: boolean
  statusLabel: string
}

export type GraphNavigatorModel = {
  edges: Array<Edge<NavigatorEdgeData>>
  nodes: Array<Node<NavigatorNodeData>>
  pathLabel?: string
}

export type SpatialGraphData = {
  links: Array<{
    isPathLink: boolean
    source: string
    status: string
    target: string
    value: number
  }>
  nodes: Array<{
    group: string
    id: string
    name: string
    risk: GraphNodeRisk
    val: number
  }>
}

type BuildNavigatorInput = {
  edgeRows: GraphExplorerEdgeResponse[]
  edges: GraphEdgeResponse[]
  focusMode: FocusMode
  layoutMode: LayoutMode
  motionEnabled: boolean
  nodes: string[]
  operationRows: OperationExplorerEntryResponse[]
  q?: string
  selectedNodeId?: string | null
  selectedPathSequence?: GraphSequenceResponse
}

export function shouldAnimateGraph(motionMode: MotionMode, prefersReducedMotion: boolean) {
  if (motionMode === 'off' || motionMode === 'reduced') return false
  return !prefersReducedMotion
}

export function findSelectedPathSequence(
  sequenceRows: GraphSequenceResponse[],
  selectedPath?: string,
  sequenceId?: string,
) {
  const pathId = selectedPath ?? sequenceId
  if (!pathId) return undefined
  return sequenceRows.find((sequence) => sequence.sequence_id === pathId)
}

export function getSequencePathLabel(sequence?: GraphSequenceResponse) {
  if (!sequence || sequence.operations.length === 0) return undefined
  return sequence.operations.join(' -> ')
}

function normalizeQuery(q: string | undefined) {
  const normalized = q?.trim().toLowerCase()
  return normalized && normalized.length > 0 ? normalized : undefined
}

function edgeKey(from: string, to: string) {
  return `${from} -> ${to}`
}

function buildPathEdgeKeys(sequence?: GraphSequenceResponse) {
  const keys = new Set<string>()
  if (!sequence) return keys
  for (let index = 0; index < sequence.operations.length - 1; index += 1) {
    keys.add(edgeKey(sequence.operations[index], sequence.operations[index + 1]))
  }
  return keys
}

function buildAllowedNodeSet(input: BuildNavigatorInput) {
  const normalizedQuery = normalizeQuery(input.q)
  const allowed = new Set<string>()

  input.nodes.forEach((node) => {
    if (!normalizedQuery || node.toLowerCase().includes(normalizedQuery)) allowed.add(node)
  })

  input.edges.forEach((edge) => {
    const matchesQuery =
      !normalizedQuery ||
      edge.from_node.toLowerCase().includes(normalizedQuery) ||
      edge.to_node.toLowerCase().includes(normalizedQuery)
    if (matchesQuery) {
      allowed.add(edge.from_node)
      allowed.add(edge.to_node)
    }
  })

  if (input.focusMode === 'neighborhood' && input.selectedNodeId) {
    const neighborhood = new Set([input.selectedNodeId])
    input.edges.forEach((edge) => {
      if (edge.from_node === input.selectedNodeId) neighborhood.add(edge.to_node)
      if (edge.to_node === input.selectedNodeId) neighborhood.add(edge.from_node)
    })
    return new Set(Array.from(allowed).filter((node) => neighborhood.has(node)))
  }

  if (input.focusMode === 'path' && input.selectedPathSequence) {
    const pathNodes = new Set(input.selectedPathSequence.operations)
    return new Set(Array.from(allowed).filter((node) => pathNodes.has(node)))
  }

  return allowed
}

function deriveRisk(operation: OperationExplorerEntryResponse | undefined, inDegree: number, outDegree: number): GraphNodeRisk {
  if (operation?.has_failures) return 'danger'
  if ((operation?.constraint_count ?? 0) >= 3) return 'warning'
  if (inDegree + outDegree >= 3) return 'warning'
  if ((operation?.test_case_count ?? 0) > 0 && inDegree + outDegree > 0) return 'success'
  return 'neutral'
}

function riskLabel(risk: GraphNodeRisk) {
  if (risk === 'danger') return 'Has failures'
  if (risk === 'warning') return 'Needs review'
  if (risk === 'success') return 'Evidence linked'
  return 'Unclassified'
}

function buildDegreeMaps(edges: GraphEdgeResponse[]) {
  const incoming = new Map<string, number>()
  const outgoing = new Map<string, number>()
  edges.forEach((edge) => {
    outgoing.set(edge.from_node, (outgoing.get(edge.from_node) ?? 0) + 1)
    incoming.set(edge.to_node, (incoming.get(edge.to_node) ?? 0) + 1)
  })
  return { incoming, outgoing }
}

function edgeRowByPair(edgeRows: GraphExplorerEdgeResponse[]) {
  return new Map(edgeRows.map((edge) => [edgeKey(edge.from_operation_id, edge.to_operation_id), edge]))
}

export function buildGraphNavigatorModel(input: BuildNavigatorInput): GraphNavigatorModel {
  const allowedNodeIds = buildAllowedNodeSet(input)
  const operationById = new Map(input.operationRows.map((operation) => [operation.operation_id, operation]))
  const rowsByPair = edgeRowByPair(input.edgeRows)
  const pathEdgeKeys = buildPathEdgeKeys(input.selectedPathSequence)
  const pathNodes = new Set(input.selectedPathSequence?.operations ?? [])
  const { incoming, outgoing } = buildDegreeMaps(input.edges)

  const flowNodes: Array<Node<NavigatorNodeData>> = Array.from(allowedNodeIds).map((node) => {
    const operation = operationById.get(node)
    const inDegree = incoming.get(node) ?? operation?.graph_in_degree ?? 0
    const outDegree = outgoing.get(node) ?? operation?.graph_out_degree ?? 0
    const risk = deriveRisk(operation, inDegree, outDegree)

    return {
      id: node,
      data: {
        degreeLabel: `${inDegree} in / ${outDegree} out`,
        isPathNode: pathNodes.has(node),
        isSelected: input.selectedNodeId === node,
        label: operation?.display_operation_id ?? node,
        operationId: node,
        risk,
        statusLabel: riskLabel(risk),
      },
      position: { x: 0, y: 0 },
      type: 'operationNode',
    }
  })

  const flowEdges: Array<Edge<NavigatorEdgeData>> = input.edges
    .filter((edge) => allowedNodeIds.has(edge.from_node) && allowedNodeIds.has(edge.to_node))
    .map((edge) => {
      const row = rowsByPair.get(edgeKey(edge.from_node, edge.to_node))
      const isPathEdge = pathEdgeKeys.has(edgeKey(edge.from_node, edge.to_node))
      return {
        animated: input.motionEnabled && isPathEdge,
        data: {
          evidenceCount: row?.evidence_count ?? edge.similar_parameters.length,
          isPathEdge,
          statusLabel: row?.edge_status ?? 'candidate',
        },
        id: getGraphEdgeId(edge),
        label: row?.evidence_count ?? edge.similar_parameters.length,
        source: edge.from_node,
        target: edge.to_node,
        type: 'evidenceEdge',
      }
    })

  return {
    edges: flowEdges,
    nodes: layoutGraph(flowNodes, flowEdges, input.layoutMode),
    pathLabel: getSequencePathLabel(input.selectedPathSequence),
  }
}

export function buildSpatialGraphData(model: GraphNavigatorModel): SpatialGraphData {
  return {
    links: model.edges.map((edge) => ({
      isPathLink: Boolean(edge.data?.isPathEdge),
      source: edge.source,
      status: edge.data?.statusLabel ?? 'candidate',
      target: edge.target,
      value: Math.max(1, edge.data?.evidenceCount ?? 1),
    })),
    nodes: model.nodes.map((node) => ({
      group: node.data.risk,
      id: node.id,
      name: node.data.label,
      risk: node.data.risk,
      val: node.data.isSelected || node.data.isPathNode ? 7 : 4,
    })),
  }
}

export function summarizeEvidenceItem(evidence: GraphEvidenceResponse) {
  const left = evidence.value1 ?? evidence.from_evidence_node_id ?? 'source value'
  const right = evidence.value2 ?? evidence.to_evidence_node_id ?? 'target value'
  return {
    label: `${left} -> ${right}`,
    relation: evidence.relation_hint ?? 'Dependency evidence',
    source: evidence.source,
    sourceArtifact: evidence.source_artifact_id,
  }
}

export function summarizeGraphEdgeDetail(edge: GraphEdgeDetailResponse) {
  return {
    evidenceItems: edge.evidence.map(summarizeEvidenceItem),
    routeLabel: `${edge.from_operation_id} -> ${edge.to_operation_id}`,
    statusLabel: edge.edge_status,
  }
}
