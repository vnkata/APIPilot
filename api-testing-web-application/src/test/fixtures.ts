import type {
  ArtifactCatalogResponse,
  ArtifactContentResponse,
  ConstraintEntryPageResponse,
  DependencyGraphResponse,
  GraphEdgePageResponse,
  HarEntryPageResponse,
  HarSessionListResponse,
  InvariantPageResponse,
  OperationDetailResponse,
  OperationListResponse,
  ReportEntryPageResponse,
  ReportsResponse,
  RunCatalogResponse,
  RunMetadataResponse,
  RunSummaryResponse,
  TestCasePageResponse,
} from '../shared/api/generated/model'

export const runA: RunMetadataResponse = {
  run_name: 'Run A',
  artifact_count: 8,
  has_history: true,
  modified_at: '2026-01-01T00:00:00Z',
  size_bytes: 42_000,
}

export const runCatalog: RunCatalogResponse = {
  runs: [runA],
}

export const runSummary: RunSummaryResponse = {
  run_name: 'Run A',
  artifact_count: 8,
  available_artifacts: {
    dynamic_constraints: true,
    graph: true,
    history: true,
    invariants: true,
    reports: true,
    specification: true,
    static_constraints: true,
    test_cases: true,
  },
  dynamic_constraint_count: 1,
  har_session_count: 1,
  operation_count: 2,
  report_status_counts: {
    '200': 1,
    '201': 1,
    '404': 1,
  },
  static_constraint_count: 3,
  test_case_count: 2,
}

export const operations: OperationListResponse = {
  run_name: 'Run A',
  operations: [
    {
      operation_id: 'get-/items',
      display_operation_id: 'ListItems',
      http_method: 'get',
      parameter_count: 1,
      path_template: '/items',
      response_statuses: ['200', '404'],
    },
    {
      operation_id: 'post-/items',
      display_operation_id: 'CreateItem',
      http_method: 'post',
      parameter_count: 0,
      path_template: '/items',
      response_statuses: ['201'],
    },
  ],
}

export const operationDetail: OperationDetailResponse = {
  operation_id: 'get-/items',
  display_operation_id: 'ListItems',
  http_method: 'get',
  parameter_count: 1,
  parameters: {
    limit: {
      name: 'limit',
      in_value: 'query',
      schema: { type: 'integer', minimum: 1 },
    },
  },
  path_template: '/items',
  request_body: {},
  response_statuses: ['200', '404'],
  responses: {
    '200': { description: 'OK' },
    '404': { description: 'Missing' },
  },
}

export const graph: DependencyGraphResponse = {
  run_name: 'Run A',
  nodes: ['get-/items', 'post-/items'],
  edges: [
    {
      from_node: 'post-/items',
      to_node: 'get-/items',
      similar_parameters: [
        {
          value1: 'item.id',
          value2: 'itemId',
          in_value: 'response to parameter via test',
        },
      ],
    },
  ],
}

export const graphEdges: GraphEdgePageResponse = {
  run_name: 'Run A',
  items: graph.edges,
  groups: [{ key: 'post-/items', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const staticConstraints: ConstraintEntryPageResponse = {
  run_name: 'Run A',
  items: [
    {
      operation_id: 'get-/items',
      property_path: 'input.limit',
      expression: 'input.limit >= 1',
      section: 'request_response',
    },
  ],
  groups: [{ key: 'request_response', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const dynamicConstraints: ConstraintEntryPageResponse = {
  run_name: 'Run A',
  items: [
    {
      operation_id: 'get-/items',
      property_path: 'return.items[].id',
      expression: 'return.items.id >= 1',
      section: null,
    },
  ],
  groups: [{ key: 'get-/items', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const invariants: InvariantPageResponse = {
  run_name: 'Run A',
  items: [
    {
      operation_id: 'get-/items',
      pptname: 'get-/items:::EXIT',
      invariant: 'return.items.id >= 1',
      invariant_type: 'daikon.inv.unary.scalar.LowerBound',
      variables: '(return.items.id)',
      postman_assertion: 'pm.expect(return_items_id).to.be.at.least(1)',
    },
  ],
  groups: [{ key: 'get-/items', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const artifactCatalog: ArtifactCatalogResponse = {
  run_name: 'Run A',
  artifacts: [
    {
      artifact_id: 'specification',
      kind: 'specification',
      media_type: 'application/json',
      modified_at: '2026-01-01T00:00:00Z',
      raw_policy: 'raw_json',
      raw_supported: true,
      relative_path: 'specification.json',
      run_name: 'Run A',
      size_bytes: 2048,
      summary_supported: true,
    },
    {
      artifact_id: 'test_cases_json',
      kind: 'test_cases',
      media_type: 'application/json',
      modified_at: '2026-01-01T00:00:00Z',
      raw_policy: 'sanitized_test_cases',
      raw_supported: true,
      relative_path: 'test_cases.json',
      run_name: 'Run A',
      size_bytes: 4096,
      summary_supported: true,
    },
    {
      artifact_id: 'invariants_csv',
      kind: 'invariants',
      media_type: 'text/csv',
      modified_at: '2026-01-01T00:00:00Z',
      raw_policy: 'raw_csv',
      raw_supported: true,
      relative_path: 'invariants.csv',
      run_name: 'Run A',
      size_bytes: 1024,
      summary_supported: true,
    },
  ],
}

export const artifactContent: ArtifactContentResponse = {
  run_name: 'Run A',
  artifact_id: 'specification',
  raw: true,
  metadata: artifactCatalog.artifacts[0],
  content: {
    content_kind: 'raw_json',
    value: {
      operations: {
        'get-/items': { method: 'get', path: '/items' },
      },
    },
  },
}

export const rawCsvArtifactContent: ArtifactContentResponse = {
  run_name: 'Run A',
  artifact_id: 'invariants_csv',
  raw: true,
  metadata: artifactCatalog.artifacts[2],
  content: {
    content_kind: 'raw_csv',
    rows: [
      {
        invariant: 'return.items.id >= 1',
        invariantType: 'daikon.inv.unary.scalar.LowerBound',
        postmanAssertion: 'pm.expect(return_items_id).to.be.at.least(1)',
        pptname: 'get-/items:::EXIT',
        variables: '(return.items.id)',
      },
    ],
  },
}

export const reports: ReportsResponse = {
  run_name: 'Run A',
  entries: [
    { operation_id: 'get-/items', status_code: '200', count: 1 },
    { operation_id: 'get-/items', status_code: '404', count: 1 },
    { operation_id: 'post-/items', status_code: '201', count: 1 },
  ],
  status_counts: {
    '200': 1,
    '201': 1,
    '404': 1,
  },
}

export const reportEntries: ReportEntryPageResponse = {
  run_name: 'Run A',
  items: [
    { operation_id: 'get-/items', status_code: '200', count: 1 },
    { operation_id: 'get-/items', status_code: '404', count: 1 },
  ],
  groups: [{ key: 'get-/items', count: 2 }],
  pagination: { limit: 25, offset: 0, total: 2 },
}

export const testCases: TestCasePageResponse = {
  run_name: 'Run A',
  items: [
    {
      test_case_id: 'tc-1',
      operation_id: 'get-/items',
      path: '/items',
      http_method: 'get',
      parameters: { limit: 1 },
      request_body: null,
      response_body: null,
      status_code: 200,
    },
  ],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const harSessions: HarSessionListResponse = {
  run_name: 'Run A',
  sessions: [
    {
      session_id: 'session-1',
      entry_count: 1,
      modified_at: '2026-01-01T00:00:00Z',
      size_bytes: 1024,
    },
  ],
}

export const harEntries: HarEntryPageResponse = {
  run_name: 'Run A',
  session_id: 'session-1',
  items: [
    {
      entry_id: 'entry-1',
      duration_ms: 12.5,
      query_params: { limit: '1' },
      request_body: null,
      request_headers: { authorization: '<REDACTED>', accept: 'application/json' },
      request_method: 'GET',
      request_url: 'https://example.test/items',
      response_body: null,
      response_headers: {
        'content-type': 'application/json',
        'set-cookie': '<REDACTED>',
      },
      response_status: 200,
      response_status_text: 'OK',
      started_at: '2026-01-01T00:00:00Z',
    },
  ],
  pagination: { limit: 25, offset: 0, total: 1 },
}
