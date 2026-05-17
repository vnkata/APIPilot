import {
  artifactsSearchSchema,
  constraintsSearchSchema,
  graphSearchSchema,
  historySearchSchema,
  operationsSearchSchema,
  runOverviewSearchSchema,
  testCasesSearchSchema,
} from './searchParams'

describe('route search params', () => {
  it('preserves URL-backed selected row ids for investigation views', () => {
    expect(operationsSearchSchema.parse({ operationKey: 'op-get-items', limit: 25, offset: 0 })).toMatchObject({
      operationKey: 'op-get-items',
    })
    expect(graphSearchSchema.parse({ edgeId: 'edge-a', limit: 25, offset: 0 })).toMatchObject({
      edgeId: 'edge-a',
    })
    expect(graphSearchSchema.parse({ sequenceId: 'seq-create-list', limit: 25, offset: 0 })).toMatchObject({
      sequenceId: 'seq-create-list',
    })
    expect(constraintsSearchSchema.parse({ constraintId: 'constraint-limit', limit: 25, offset: 0 })).toMatchObject({
      constraintId: 'constraint-limit',
      constraintTab: 'explorer',
    })
    expect(constraintsSearchSchema.parse({ invariantId: 'inv-limit', limit: 25, offset: 0 })).toMatchObject({
      invariantId: 'inv-limit',
      constraintTab: 'explorer',
    })
    expect(testCasesSearchSchema.parse({ testCaseId: 'tc-1', limit: 25, offset: 0 })).toMatchObject({
      testCaseId: 'tc-1',
    })
    expect(historySearchSchema.parse({ entryId: 'entry-1', limit: 25, offset: 0 })).toMatchObject({
      entryId: 'entry-1',
    })
  })

  it('parses visible explorer filters with camelCase URL params', () => {
    expect(
      operationsSearchSchema.parse({
        groupBy: 'http_method',
        hasConstraints: 'true',
        hasFailures: 'false',
        httpMethod: 'get',
        limit: '10',
        offset: '20',
        responseStatus: '404',
        sortBy: 'constraint_count',
        sortOrder: 'desc',
      }),
    ).toMatchObject({
      groupBy: 'http_method',
      hasConstraints: true,
      hasFailures: false,
      httpMethod: 'get',
      limit: 10,
      offset: 20,
      responseStatus: '404',
      sortBy: 'constraint_count',
      sortOrder: 'desc',
    })

    expect(
      graphSearchSchema.parse({
        edgeStatus: 'candidate',
        evidenceSource: 'gpt_edges',
        graphTab: 'nodes',
        nodeKind: 'operation',
        sequenceType: 'dependency_chain',
      }),
    ).toMatchObject({
      edgeStatus: 'candidate',
      evidenceSource: 'gpt_edges',
      graphTab: 'nodes',
      nodeKind: 'operation',
      sequenceType: 'dependency_chain',
    })

    expect(
      constraintsSearchSchema.parse({
        agreementStatus: 'both_present',
        assertionAvailable: 'true',
        constraintKind: 'bounds',
        constraintTab: 'invariants',
        correlationConfidence: 'exact',
        oracleReadiness: 'verified_runtime_oracle',
        source: 'combined',
      }),
    ).toMatchObject({
      agreementStatus: 'both_present',
      assertionAvailable: true,
      constraintKind: 'bounds',
      constraintTab: 'invariants',
      correlationConfidence: 'exact',
      oracleReadiness: 'verified_runtime_oracle',
      source: 'combined',
    })
  })

  it('parses route-specific view modes with backward-compatible defaults', () => {
    expect(runOverviewSearchSchema.parse({})).toMatchObject({ overviewView: 'classic' })
    expect(operationsSearchSchema.parse({})).toMatchObject({ operationsView: 'table' })
    expect(constraintsSearchSchema.parse({})).toMatchObject({
      constraintDetailView: 'readable',
      constraintsView: 'workbench',
      matrixBy: 'source',
    })
    expect(graphSearchSchema.parse({})).toMatchObject({
      focusMode: 'all',
      graphView: 'explorer',
      motionMode: 'auto',
    })
    expect(artifactsSearchSchema.parse({})).toMatchObject({ artifactsView: 'classic' })

    expect(runOverviewSearchSchema.parse({ overviewView: 'command' })).toMatchObject({ overviewView: 'command' })
    expect(operationsSearchSchema.parse({ operationsView: 'canvas' })).toMatchObject({ operationsView: 'canvas' })
    expect(operationsSearchSchema.parse({ operationsView: 'cards' })).toMatchObject({ operationsView: 'cards' })
    expect(constraintsSearchSchema.parse({ constraintsView: 'workbench' })).toMatchObject({ constraintsView: 'workbench' })
    expect(constraintsSearchSchema.parse({ constraintDetailView: 'raw' })).toMatchObject({ constraintDetailView: 'raw' })
    expect(constraintsSearchSchema.parse({ matrixBy: 'kind' })).toMatchObject({ matrixBy: 'kind' })
    expect(constraintsSearchSchema.parse({ matrixBy: 'readiness' })).toMatchObject({ matrixBy: 'readiness' })
    expect(constraintsSearchSchema.parse({ constraintsView: 'matrix' })).toMatchObject({ constraintsView: 'matrix' })
    expect(constraintsSearchSchema.parse({ constraintsView: 'table' })).toMatchObject({ constraintsView: 'table' })
    expect(graphSearchSchema.parse({ focusMode: 'neighborhood' })).toMatchObject({ focusMode: 'neighborhood' })
    expect(graphSearchSchema.parse({ focusMode: 'path' })).toMatchObject({ focusMode: 'path' })
    expect(graphSearchSchema.parse({ graphView: 'journey' })).toMatchObject({ graphView: 'journey' })
    expect(graphSearchSchema.parse({ graphView: 'spatial' })).toMatchObject({ graphView: 'spatial' })
    expect(graphSearchSchema.parse({ motionMode: 'reduced' })).toMatchObject({ motionMode: 'reduced' })
    expect(graphSearchSchema.parse({ motionMode: 'off' })).toMatchObject({ motionMode: 'off' })
    expect(graphSearchSchema.parse({ selectedPath: 'seq-create-list' })).toMatchObject({ selectedPath: 'seq-create-list' })
    expect(artifactsSearchSchema.parse({ artifactsView: 'workbench' })).toMatchObject({ artifactsView: 'workbench' })

    expect(runOverviewSearchSchema.parse({ overviewView: 'timeline' })).toMatchObject({ overviewView: 'classic' })
    expect(operationsSearchSchema.parse({ operationsView: 'timeline' })).toMatchObject({ operationsView: 'table' })
    expect(constraintsSearchSchema.parse({ constraintsView: 'timeline' })).toMatchObject({ constraintsView: 'workbench' })
    expect(constraintsSearchSchema.parse({ constraintDetailView: 'timeline' })).toMatchObject({ constraintDetailView: 'readable' })
    expect(constraintsSearchSchema.parse({ matrixBy: 'timeline' })).toMatchObject({ matrixBy: 'source' })
    expect(graphSearchSchema.parse({ focusMode: 'timeline' })).toMatchObject({ focusMode: 'all' })
    expect(graphSearchSchema.parse({ graphView: 'timeline' })).toMatchObject({ graphView: 'explorer' })
    expect(graphSearchSchema.parse({ motionMode: 'timeline' })).toMatchObject({ motionMode: 'auto' })
    expect(artifactsSearchSchema.parse({ artifactsView: 'timeline' })).toMatchObject({ artifactsView: 'classic' })
  })
})
