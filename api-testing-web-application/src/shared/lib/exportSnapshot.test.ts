import { buildExportSnapshot } from './exportSnapshot'

describe('buildExportSnapshot', () => {
  it('includes selected non-body context while stripping body fields by default', () => {
    const snapshot = buildExportSnapshot({
      data: {
        rows: [
          {
            request_body: { secret: 'hidden' },
            response_body: { id: 1 },
            status_code: 200,
          },
        ],
      },
      filters: { testCaseId: 'tc-1' },
      includeBodies: false,
      route: '/runs/Run%20A/test-cases',
      selectedContext: {
        request_body: { secret: 'hidden' },
        response_body: { id: 1 },
        status_code: 200,
        test_case_id: 'tc-1',
      },
      title: 'Test cases',
    })

    expect(snapshot).toMatchObject({
      filters: { testCaseId: 'tc-1' },
      include_bodies: false,
      selected_context: {
        status_code: 200,
        test_case_id: 'tc-1',
      },
    })
    expect(JSON.stringify(snapshot)).not.toContain('request_body')
    expect(JSON.stringify(snapshot)).not.toContain('response_body')
  })
})
