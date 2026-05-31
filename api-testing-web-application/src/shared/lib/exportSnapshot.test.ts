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

  it('redacts sensitive nested keys even when visible bodies are explicitly included', () => {
    const snapshot = buildExportSnapshot({
      data: {
        rows: [
          {
            authorization: 'Bearer test-token',
            body: {
              access_token: 'nested-token',
              items: [{ api_key: 'key-1' }],
              safe: 'visible',
            },
            cookie: 'session=abc',
          },
        ],
      },
      filters: {
        sessionId: 'session-1',
      },
      includeBodies: true,
      route: '/runs/Run%20A/history',
      selectedContext: {
        headers: {
          password: 'hidden',
          trace_id: 'trace-1',
        },
      },
      title: 'History',
    })

    expect(JSON.stringify(snapshot)).not.toContain('test-token')
    expect(JSON.stringify(snapshot)).not.toContain('nested-token')
    expect(JSON.stringify(snapshot)).not.toContain('key-1')
    expect(JSON.stringify(snapshot)).not.toContain('session=abc')
    expect(snapshot).toMatchObject({
      data: {
        rows: [
          {
            authorization: '<REDACTED>',
            body: {
              access_token: '<REDACTED>',
              items: [{ api_key: '<REDACTED>' }],
              safe: 'visible',
            },
            cookie: '<REDACTED>',
          },
        ],
      },
      selected_context: {
        headers: {
          password: '<REDACTED>',
          trace_id: 'trace-1',
        },
      },
    })
  })

  it('keeps local notes and bookmarks out of exports unless explicitly included', () => {
    const snapshotWithoutLocalContext = buildExportSnapshot({
      data: { rows: [] },
      includeBodies: false,
      localContext: {
        bookmarks: [{ label: 'ListItems' }],
        notes: [{ note: 'May include a pasted token secret-value' }],
      },
      route: '/runs/Run%20A/workspace',
      title: 'Workspace',
    })

    expect(JSON.stringify(snapshotWithoutLocalContext)).not.toContain('ListItems')
    expect(JSON.stringify(snapshotWithoutLocalContext)).not.toContain('secret-value')

    const snapshotWithLocalContext = buildExportSnapshot({
      data: { rows: [] },
      includeBodies: false,
      includeLocalContext: true,
      localContext: {
        bookmarks: [{ label: 'ListItems' }],
        notes: [{ note: 'Review evidence', token: 'secret-value' }],
      },
      route: '/runs/Run%20A/workspace',
      title: 'Workspace',
    })

    expect(snapshotWithLocalContext).toMatchObject({
      include_local_context: true,
      local_context: {
        bookmarks: [{ label: 'ListItems' }],
        notes: [{ note: 'Review evidence', token: '<REDACTED>' }],
      },
      redaction_summary: {
        redacted_fields: expect.any(Number),
      },
    })
    expect(JSON.stringify(snapshotWithLocalContext)).not.toContain('secret-value')
  })
})
