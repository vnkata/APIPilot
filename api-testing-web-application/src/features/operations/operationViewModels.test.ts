import { operationExplorerDetail, operationExplorerEntries } from '../../test/fixtures'
import {
  buildOperationMissionBoard,
  summarizeOperationDetail,
} from './operationViewModels'

describe('operation view models', () => {
  it('assigns visible operations to mission board lanes by triage priority', () => {
    const board = buildOperationMissionBoard([
      ...operationExplorerEntries.items,
      {
        ...operationExplorerEntries.items[1],
        constraint_count: 0,
        graph_in_degree: 2,
        graph_out_degree: 2,
        operation_id: 'patch-/items/{id}',
        operation_key: 'op-patch-items',
      },
      {
        ...operationExplorerEntries.items[1],
        constraint_count: 3,
        invariant_count: 2,
        operation_id: 'delete-/items/{id}',
        operation_key: 'op-delete-items',
      },
      {
        ...operationExplorerEntries.items[1],
        graph_in_degree: 0,
        graph_out_degree: 0,
        operation_id: 'head-/items',
        operation_key: 'op-head-items',
        test_case_count: 0,
      },
    ])

    expect(board.metrics).toMatchObject({
      failures: 1,
      visible: 5,
    })
    expect(board.lanes.find((lane) => lane.id === 'failures')?.operations).toHaveLength(1)
    expect(board.lanes.find((lane) => lane.id === 'high_dependency')?.operations[0]?.operation_key).toBe('op-patch-items')
    expect(board.lanes.find((lane) => lane.id === 'constraint_heavy')?.operations[0]?.operation_key).toBe('op-delete-items')
    expect(board.lanes.find((lane) => lane.id === 'low_evidence')?.operations[0]?.operation_key).toBe('op-head-items')
    expect(board.lanes.find((lane) => lane.id === 'ready')?.operations[0]?.operation_key).toBe('op-post-items')
  })

  it('summarizes operation detail into readable sections and raw fallback', () => {
    const summary = summarizeOperationDetail(operationExplorerDetail)

    expect(summary.relatedGroups).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ label: 'Incoming edges', values: ['edge-create-list'] }),
        expect.objectContaining({ label: 'Constraints', values: ['constraint-limit'] }),
      ]),
    )
    expect(summary.parameterItems[0]).toMatchObject({ name: 'limit', location: 'query' })
    expect(summary.responseItems[0]).toMatchObject({ status: '200' })
    expect(summary.raw).toHaveProperty('parameters')
  })
})
