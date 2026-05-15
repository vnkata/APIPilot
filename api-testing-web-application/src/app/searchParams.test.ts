import {
  constraintsSearchSchema,
  graphSearchSchema,
  historySearchSchema,
  operationsSearchSchema,
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
})
