import {
  graphSearchSchema,
  historySearchSchema,
  testCasesSearchSchema,
} from './searchParams'

describe('route search params', () => {
  it('preserves URL-backed selected row ids for investigation views', () => {
    expect(graphSearchSchema.parse({ edgeId: 'edge-a', limit: 25, offset: 0 })).toMatchObject({
      edgeId: 'edge-a',
    })
    expect(testCasesSearchSchema.parse({ testCaseId: 'tc-1', limit: 25, offset: 0 })).toMatchObject({
      testCaseId: 'tc-1',
    })
    expect(historySearchSchema.parse({ entryId: 'entry-1', limit: 25, offset: 0 })).toMatchObject({
      entryId: 'entry-1',
    })
  })
})
