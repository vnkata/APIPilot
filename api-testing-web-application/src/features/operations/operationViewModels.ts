import type {
  OperationExplorerDetailResponse,
  OperationExplorerEntryResponse,
} from '../../shared/api/generated/model'

export type OperationLaneId =
  | 'constraint_heavy'
  | 'failures'
  | 'high_dependency'
  | 'low_evidence'
  | 'ready'

export type OperationMissionLane = {
  description: string
  id: OperationLaneId
  operations: OperationExplorerEntryResponse[]
  title: string
}

export type OperationMissionBoard = {
  lanes: OperationMissionLane[]
  metrics: {
    constraints: number
    failures: number
    graphLinked: number
    lowEvidence: number
    visible: number
  }
}

export type OperationDetailSummary = {
  parameterItems: Array<{ location: string; name: string; summary: string }>
  raw: {
    parameters: OperationExplorerDetailResponse['parameters']
    relatedIds: {
      incoming_edge_ids: string[]
      outgoing_edge_ids: string[]
      related_constraint_ids: string[]
      related_invariant_ids: string[]
    }
    responses: OperationExplorerDetailResponse['responses']
  }
  relatedGroups: Array<{ label: string; values: string[] }>
  responseItems: Array<{ status: string; summary: string }>
}

function dependencyDegree(operation: OperationExplorerEntryResponse) {
  return operation.graph_in_degree + operation.graph_out_degree
}

function isConstraintHeavy(operation: OperationExplorerEntryResponse) {
  return operation.constraint_count + operation.invariant_count >= 3
}

function isLowEvidence(operation: OperationExplorerEntryResponse) {
  return operation.test_case_count === 0 || dependencyDegree(operation) === 0
}

function laneForOperation(operation: OperationExplorerEntryResponse): OperationLaneId {
  if (operation.has_failures) return 'failures'
  if (dependencyDegree(operation) >= 3) return 'high_dependency'
  if (isConstraintHeavy(operation)) return 'constraint_heavy'
  if (isLowEvidence(operation)) return 'low_evidence'
  return 'ready'
}

export function buildOperationMissionBoard(rows: OperationExplorerEntryResponse[]): OperationMissionBoard {
  const laneMap: Record<OperationLaneId, OperationExplorerEntryResponse[]> = {
    constraint_heavy: [],
    failures: [],
    high_dependency: [],
    low_evidence: [],
    ready: [],
  }

  rows.forEach((operation) => {
    laneMap[laneForOperation(operation)].push(operation)
  })

  return {
    lanes: [
      {
        description: 'Visible operations with failed reports or generated failure signals.',
        id: 'failures',
        operations: laneMap.failures,
        title: 'Failure lane',
      },
      {
        description: 'Visible operations with many dependency graph connections.',
        id: 'high_dependency',
        operations: laneMap.high_dependency,
        title: 'High dependency',
      },
      {
        description: 'Visible operations carrying dense constraints or invariants.',
        id: 'constraint_heavy',
        operations: laneMap.constraint_heavy,
        title: 'Constraint-heavy',
      },
      {
        description: 'Visible operations with little test or graph evidence.',
        id: 'low_evidence',
        operations: laneMap.low_evidence,
        title: 'Low evidence',
      },
      {
        description: 'Visible operations with linked evidence and no failure signal.',
        id: 'ready',
        operations: laneMap.ready,
        title: 'Ready to inspect',
      },
    ],
    metrics: {
      constraints: rows.reduce((total, operation) => total + operation.constraint_count, 0),
      failures: rows.filter((operation) => operation.has_failures).length,
      graphLinked: rows.filter((operation) => dependencyDegree(operation) > 0).length,
      lowEvidence: rows.filter(isLowEvidence).length,
      visible: rows.length,
    },
  }
}

function summarizeJsonLike(value: unknown) {
  if (value === null || value === undefined) return 'No schema'
  if (typeof value !== 'object') return String(value)
  if (Array.isArray(value)) return `${value.length} items`
  const record = value as Record<string, unknown>
  if (typeof record.description === 'string') return record.description
  if (typeof record.type === 'string') return `type: ${record.type}`
  return `${Object.keys(record).length} fields`
}

function parameterLocation(value: unknown) {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    const record = value as Record<string, unknown>
    if (typeof record.in_value === 'string') return record.in_value
    if (typeof record.in === 'string') return record.in
  }
  return 'unknown'
}

export function summarizeOperationDetail(detail: OperationExplorerDetailResponse): OperationDetailSummary {
  const relatedGroups = [
    { label: 'Incoming edges', values: detail.incoming_edge_ids },
    { label: 'Outgoing edges', values: detail.outgoing_edge_ids },
    { label: 'Constraints', values: detail.related_constraint_ids },
    { label: 'Invariants', values: detail.related_invariant_ids },
  ]

  return {
    parameterItems: Object.entries(detail.parameters).map(([name, value]) => ({
      location: parameterLocation(value),
      name,
      summary: summarizeJsonLike(value),
    })),
    raw: {
      parameters: detail.parameters,
      relatedIds: {
        incoming_edge_ids: detail.incoming_edge_ids,
        outgoing_edge_ids: detail.outgoing_edge_ids,
        related_constraint_ids: detail.related_constraint_ids,
        related_invariant_ids: detail.related_invariant_ids,
      },
      responses: detail.responses,
    },
    relatedGroups,
    responseItems: Object.entries(detail.responses).map(([status, value]) => ({
      status,
      summary: summarizeJsonLike(value),
    })),
  }
}
