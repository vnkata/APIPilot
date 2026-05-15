import type {
  ArtifactCatalogResponse,
  ArtifactContentResponse,
  ConstraintExplorerDetailResponse,
  ConstraintExplorerPageResponse,
  ConstraintFacetsResponse,
  ConstraintEntryPageResponse,
  DependencyGraphResponse,
  GraphEdgeDetailResponse,
  GraphEdgePageResponse,
  GraphFacetsResponse,
  GraphNodePageResponse,
  GraphSequencePageResponse,
  GraphSequenceResponse,
  HarEntryPageResponse,
  HarSessionListResponse,
  InvariantExplorerDetailResponse,
  InvariantExplorerFacetsResponse,
  InvariantExplorerPageResponse,
  InvariantPageResponse,
  OperationDetailResponse,
  OperationExplorerDetailResponse,
  OperationExplorerPageResponse,
  OperationFacetsResponse,
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
  items: [
    {
      edge_id: 'edge-create-list',
      edge_status: 'final',
      evidence_count: 1,
      evidence_preview: ['item.id -> itemId'],
      evidence_sources: ['final_graph'],
      from_node: 'post-/items',
      from_node_id: 'operation:post-/items',
      from_operation_id: 'post-/items',
      similar_parameters: [
        {
          value1: 'item.id',
          value2: 'itemId',
          in_value: 'response to parameter via test',
        },
      ],
      to_node: 'get-/items',
      to_node_id: 'operation:get-/items',
      to_operation_id: 'get-/items',
    },
  ],
  groups: [{ key: 'post-/items', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const graphEdgeDetail: GraphEdgeDetailResponse = {
  ...graphEdges.items[0],
  evidence: [
    {
      evidence_id: 'evidence-create-list',
      from_evidence_node_id: 'response.item.id',
      relation_hint: 'response to parameter via test',
      source: 'final_graph',
      source_artifact_id: 'dependency_graph',
      to_evidence_node_id: 'query.itemId',
      value1: 'item.id',
      value2: 'itemId',
    },
  ],
}

export const graphFacets: GraphFacetsResponse = {
  edge_status: [{ key: 'final', count: 1 }],
  evidence_source: [{ key: 'final_graph', count: 1 }],
  from_operation_id: [{ key: 'post-/items', count: 1 }],
  node_kind: [{ key: 'operation', count: 2 }],
  sequence_type: [{ key: 'dependency_chain', count: 1 }],
  to_operation_id: [{ key: 'get-/items', count: 1 }],
}

export const graphNodes: GraphNodePageResponse = {
  run_name: 'Run A',
  items: [
    {
      http_method: 'get',
      in_degree: 1,
      label: 'ListItems',
      node_id: 'operation:get-/items',
      node_kind: 'operation',
      operation_id: 'get-/items',
      out_degree: 0,
      path_template: '/items',
    },
    {
      http_method: 'post',
      in_degree: 0,
      label: 'CreateItem',
      node_id: 'operation:post-/items',
      node_kind: 'operation',
      operation_id: 'post-/items',
      out_degree: 1,
      path_template: '/items',
    },
  ],
  groups: [{ key: 'operation', count: 2 }],
  pagination: { limit: 25, offset: 0, total: 2 },
}

export const graphSequenceDetail: GraphSequenceResponse = {
  length: 2,
  operations: ['post-/items', 'get-/items'],
  parameter_sources: [
    {
      parameter_name: 'itemId',
      source_operation_id: 'post-/items',
      source_property_path: 'item.id',
    },
  ],
  score: 0.92,
  sequence_id: 'seq-create-list',
  sequence_type: 'dependency_chain',
  target_operation_id: 'get-/items',
}

export const graphSequences: GraphSequencePageResponse = {
  run_name: 'Run A',
  items: [graphSequenceDetail],
  groups: [{ key: 'dependency_chain', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const operationExplorerEntries: OperationExplorerPageResponse = {
  run_name: 'Run A',
  items: [
    {
      constraint_count: 2,
      display_operation_id: 'ListItems',
      graph_in_degree: 1,
      graph_out_degree: 0,
      has_failures: true,
      http_method: 'get',
      invariant_count: 1,
      operation_id: 'get-/items',
      operation_key: 'op-get-items',
      parameter_count: 1,
      path_template: '/items',
      response_status_count: 2,
      response_statuses: ['200', '404'],
      test_case_count: 1,
    },
    {
      constraint_count: 1,
      display_operation_id: 'CreateItem',
      graph_in_degree: 0,
      graph_out_degree: 1,
      has_failures: false,
      http_method: 'post',
      invariant_count: 0,
      operation_id: 'post-/items',
      operation_key: 'op-post-items',
      parameter_count: 0,
      path_template: '/items',
      response_status_count: 1,
      response_statuses: ['201'],
      test_case_count: 1,
    },
  ],
  groups: [{ key: 'get', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 2 },
}

export const operationExplorerDetail: OperationExplorerDetailResponse = {
  constraint_count: 2,
  constraint_summary: { by_kind: { bounds: 1, required: 1 }, total: 2 },
  display_operation_id: 'ListItems',
  graph_in_degree: 1,
  graph_out_degree: 0,
  graph_summary: { in_degree: 1, incoming_edge_count: 1, out_degree: 0, outgoing_edge_count: 0 },
  has_failures: true,
  http_method: 'get',
  incoming_edge_ids: ['edge-create-list'],
  invariant_count: 1,
  invariant_summary: { by_kind: { bounds: 1 }, total: 1 },
  operation_id: 'get-/items',
  operation_key: 'op-get-items',
  outgoing_edge_ids: [],
  parameter_count: 1,
  parameters: operationDetail.parameters,
  path_template: '/items',
  related_constraint_ids: ['constraint-limit'],
  related_invariant_ids: ['inv-limit'],
  report_status_counts: { '200': 1, '404': 1 },
  request_body: { should_not_export_by_default: true },
  response_status_count: 2,
  response_statuses: ['200', '404'],
  responses: operationDetail.responses,
  test_case_count: 1,
  test_case_status_counts: { passed: 1 },
}

export const operationFacets: OperationFacetsResponse = {
  has_constraints: [{ key: 'true', count: 2 }],
  has_failures: [
    { key: 'true', count: 1 },
    { key: 'false', count: 1 },
  ],
  has_graph_edges: [{ key: 'true', count: 2 }],
  has_invariants: [
    { key: 'true', count: 1 },
    { key: 'false', count: 1 },
  ],
  has_request_body: [
    { key: 'true', count: 1 },
    { key: 'false', count: 1 },
  ],
  http_method: [
    { key: 'get', count: 1 },
    { key: 'post', count: 1 },
  ],
  response_status: [
    { key: '200', count: 1 },
    { key: '404', count: 1 },
  ],
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

export const constraintExplorerEntries: ConstraintExplorerPageResponse = {
  run_name: 'Run A',
  items: [
    {
      agreement_status: 'both_present',
      assertion_available: true,
      assertion_preview: 'pm.expect(input.limit).to.be.at.least(1)',
      combined_expression: 'input.limit >= 1',
      constraint_id: 'constraint-limit',
      constraint_kind: 'bounds',
      dynamic_expression: 'return.items.id >= 1',
      expression: 'input.limit >= 1',
      has_dynamic: true,
      has_static: true,
      operation_id: 'get-/items',
      parameter: 'limit',
      property_path: 'input.limit',
      section: 'request_response',
      source: 'combined',
      source_type: 'constraints',
      static_expression: 'input.limit >= 1',
    },
  ],
  groups: [{ key: 'combined', count: 1 }],
  metadata: { combined_source: 'artifact', warnings: [] },
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const constraintExplorerDetail: ConstraintExplorerDetailResponse = {
  ...constraintExplorerEntries.items[0],
  assertion: 'pm.expect(input.limit).to.be.at.least(1)',
}

export const constraintFacets: ConstraintFacetsResponse = {
  agreement_status: [{ key: 'both_present', count: 1 }],
  assertion_available: [{ key: 'true', count: 1 }],
  constraint_kind: [{ key: 'bounds', count: 1 }],
  metadata: { combined_source: 'artifact', warnings: [] },
  operation_id: [{ key: 'get-/items', count: 1 }],
  section: [{ key: 'request_response', count: 1 }],
  source: [{ key: 'combined', count: 1 }],
  source_type: [{ key: 'constraints', count: 1 }],
}

export const invariantExplorerEntries: InvariantExplorerPageResponse = {
  run_name: 'Run A',
  items: [
    {
      assertion_available: true,
      assertion_preview: 'pm.expect(return_items_id).to.be.at.least(1)',
      correlation_confidence: 'exact',
      correlation_evidence: [
        {
          constraint_id: 'constraint-limit',
          evidence_type: 'property_match',
          message: 'property path matched input.limit',
          property_path: 'input.limit',
        },
      ],
      invariant: 'return.items.id >= 1',
      invariant_id: 'inv-limit',
      invariant_kind: 'bounds',
      invariant_type: 'daikon.inv.unary.scalar.LowerBound',
      operation_id: 'get-/items',
      oracle_readiness: 'verified_runtime_oracle',
      postman_assertion: 'pm.expect(return_items_id).to.be.at.least(1)',
      pptname: 'get-/items:::EXIT',
      primary_property_path: 'return.items.id',
      property_paths: ['return.items.id'],
      related_constraint_ids: ['constraint-limit'],
      variables: '(return.items.id)',
    },
  ],
  groups: [{ key: 'verified_runtime_oracle', count: 1 }],
  pagination: { limit: 25, offset: 0, total: 1 },
}

export const invariantExplorerDetail: InvariantExplorerDetailResponse = invariantExplorerEntries.items[0]

export const invariantExplorerFacets: InvariantExplorerFacetsResponse = {
  assertion_available: [{ key: 'true', count: 1 }],
  correlation_confidence: [{ key: 'exact', count: 1 }],
  invariant_kind: [{ key: 'bounds', count: 1 }],
  invariant_type: [{ key: 'daikon.inv.unary.scalar.LowerBound', count: 1 }],
  operation_id: [{ key: 'get-/items', count: 1 }],
  oracle_readiness: [{ key: 'verified_runtime_oracle', count: 1 }],
  primary_property_path: [{ key: 'return.items.id', count: 1 }],
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
