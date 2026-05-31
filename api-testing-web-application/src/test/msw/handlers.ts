import { http, HttpResponse } from 'msw'

import {
  artifactCatalog,
  artifactContent,
  constraintExplorerDetail,
  constraintExplorerEntries,
  constraintFacets,
  dynamicConstraints,
  executionCatalog,
  executionCompleted,
  executionEvents,
  graph,
  graphEdgeDetail,
  graphEdges,
  graphFacets,
  graphNodes,
  graphSequenceDetail,
  graphSequences,
  harEntries,
  harSessions,
  invariantExplorerDetail,
  invariantExplorerEntries,
  invariantExplorerFacets,
  invariants,
  operationDetail,
  operationExplorerDetail,
  operationExplorerEntries,
  operationFacets,
  operations,
  rawCsvArtifactContent,
  reportEntries,
  reports,
  runA,
  runCatalog,
  runConfig,
  runConfigCatalog,
  runSummary,
  specCatalog,
  specOperations,
  staticConstraints,
  testCases,
  uploadedSpec,
} from '../fixtures'

const api = (path: string) => `*/api/v1${path}`
let latestUploadedSpec = uploadedSpec

export const handlers = [
  http.get('*/health', () => HttpResponse.json({ status: 'ok' })),
  http.get(api('/specs'), () => HttpResponse.json({ ...specCatalog, specs: [latestUploadedSpec] })),
  http.post(api('/specs'), async ({ request }) => {
    const body = await request.json() as { filename?: string; title?: string }
    latestUploadedSpec = {
      ...uploadedSpec,
      filename: body.filename ?? uploadedSpec.filename,
      title: body.title || uploadedSpec.title,
    }
    return HttpResponse.json(latestUploadedSpec, { status: 201 })
  }),
  http.get(api('/specs/:specId'), () => HttpResponse.json(uploadedSpec)),
  http.get(api('/specs/:specId/operations'), () => HttpResponse.json(specOperations)),
  http.get(api('/run-configs'), () => HttpResponse.json(runConfigCatalog)),
  http.post(api('/run-configs/validate'), () => HttpResponse.json({ valid: true, errors: [] })),
  http.post(api('/run-configs'), () => HttpResponse.json(runConfig, { status: 201 })),
  http.get(api('/run-configs/:runConfigId'), () => HttpResponse.json(runConfig)),
  http.get(api('/executions'), () => HttpResponse.json(executionCatalog)),
  http.post(api('/executions'), () => HttpResponse.json(executionCompleted, { status: 202 })),
  http.get(api('/executions/:executionId'), () => HttpResponse.json(executionCompleted)),
  http.post(api('/executions/:executionId/cancel'), () =>
    HttpResponse.json({ ...executionCompleted, status: 'cancel_requested' }),
  ),
  http.get(api('/executions/:executionId/events'), () => HttpResponse.json(executionEvents)),
  http.get(api('/executions/:executionId/run'), () =>
    HttpResponse.json({ execution_id: executionCompleted.execution_id, run_name: executionCompleted.run_name }),
  ),
  http.get(api('/runs'), () => HttpResponse.json(runCatalog)),
  http.get(api('/runs/:runName'), ({ params }) => {
    return params.runName === 'Run A'
      ? HttpResponse.json(runA)
      : HttpResponse.json({ error: { code: 'not_found', message: 'Run not found' } }, { status: 404 })
  }),
  http.get(api('/runs/:runName/summary'), ({ params }) => {
    return params.runName === 'Run A'
      ? HttpResponse.json(runSummary)
      : HttpResponse.json({ error: { code: 'not_found', message: 'Run not found' } }, { status: 404 })
  }),
  http.get(api('/runs/:runName/artifacts'), () => HttpResponse.json(artifactCatalog)),
  http.get(api('/runs/:runName/artifacts/:artifactId/content'), ({ params }) =>
    HttpResponse.json(params.artifactId === 'invariants_csv' ? rawCsvArtifactContent : artifactContent),
  ),
  http.get(api('/runs/:runName/operations'), () => HttpResponse.json(operations)),
  http.get(api('/runs/:runName/operation'), () => HttpResponse.json(operationDetail)),
  http.get(api('/runs/:runName/operations/entries'), () => HttpResponse.json(operationExplorerEntries)),
  http.get(api('/runs/:runName/operations/entries/:operationKey'), () =>
    HttpResponse.json(operationExplorerDetail),
  ),
  http.get(api('/runs/:runName/operations/facets'), () => HttpResponse.json(operationFacets)),
  http.get(api('/runs/:runName/reports'), () => HttpResponse.json(reports)),
  http.get(api('/runs/:runName/reports/entries'), () => HttpResponse.json(reportEntries)),
  http.get(api('/runs/:runName/graph'), () => HttpResponse.json(graph)),
  http.get(api('/runs/:runName/graph/edges'), () => HttpResponse.json(graphEdges)),
  http.get(api('/runs/:runName/graph/edges/:edgeId'), () => HttpResponse.json(graphEdgeDetail)),
  http.get(api('/runs/:runName/graph/facets'), () => HttpResponse.json(graphFacets)),
  http.get(api('/runs/:runName/graph/nodes'), () => HttpResponse.json(graphNodes)),
  http.get(api('/runs/:runName/graph/sequences'), () => HttpResponse.json(graphSequences)),
  http.get(api('/runs/:runName/graph/sequences/:sequenceId'), () =>
    HttpResponse.json(graphSequenceDetail),
  ),
  http.get(api('/runs/:runName/constraints/static'), () =>
    HttpResponse.json({ run_name: 'Run A', sections: [] }),
  ),
  http.get(api('/runs/:runName/constraints/static/entries'), () => HttpResponse.json(staticConstraints)),
  http.get(api('/runs/:runName/constraints/dynamic'), () =>
    HttpResponse.json({ run_name: 'Run A', operation_count: 1, constraint_count: 1 }),
  ),
  http.get(api('/runs/:runName/constraints/dynamic/entries'), () => HttpResponse.json(dynamicConstraints)),
  http.get(api('/runs/:runName/constraints/dynamic/invariants'), () => HttpResponse.json(invariants)),
  http.get(api('/runs/:runName/constraints/entries'), () => HttpResponse.json(constraintExplorerEntries)),
  http.get(api('/runs/:runName/constraints/entries/:constraintId'), () =>
    HttpResponse.json(constraintExplorerDetail),
  ),
  http.get(api('/runs/:runName/constraints/facets'), () => HttpResponse.json(constraintFacets)),
  http.get(api('/runs/:runName/constraints/invariants'), () => HttpResponse.json(invariantExplorerEntries)),
  http.get(api('/runs/:runName/constraints/invariants/facets'), () =>
    HttpResponse.json(invariantExplorerFacets),
  ),
  http.get(api('/runs/:runName/constraints/invariants/:invariantId'), () =>
    HttpResponse.json(invariantExplorerDetail),
  ),
  http.get(api('/runs/:runName/test-cases'), () => HttpResponse.json(testCases)),
  http.get(api('/runs/:runName/history/sessions'), () => HttpResponse.json(harSessions)),
  http.get(api('/runs/:runName/history/sessions/:sessionId/entries'), () => HttpResponse.json(harEntries)),
]
