import { http, HttpResponse } from 'msw'

import {
  artifactCatalog,
  artifactContent,
  combinationDetail,
  combinationEntries,
  combinationFacets,
  combinationReview,
  combinationSummary,
  combineArtifactContent,
  constraintExplorerDetail,
  constraintExplorerEntries,
  constraintFacets,
  constraintResearchDetail,
  constraintResearchEntries,
  constraintResearchSummary,
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
  contextualMemoryDbSummaryContent,
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
  http.get(api('/runs/:runName/artifacts/:artifactId/content'), ({ params }) => {
    if (params.artifactId === 'invariants_csv') return HttpResponse.json(rawCsvArtifactContent)
    if (params.artifactId === 'combine_constraint_miners') return HttpResponse.json(combineArtifactContent)
    if (params.artifactId === 'contextual_memory_db') return HttpResponse.json(contextualMemoryDbSummaryContent)
    return HttpResponse.json(artifactContent)
  }),
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
  http.get(api('/runs/:runName/constraints/combination/summary'), () => HttpResponse.json(combinationSummary)),
  http.get(api('/runs/:runName/constraints/combination/entries'), () => HttpResponse.json(combinationEntries)),
  http.get(api('/runs/:runName/constraints/combination/entries/:combinationId'), () =>
    HttpResponse.json(combinationDetail),
  ),
  http.get(api('/runs/:runName/constraints/combination/entries/:combinationId/review'), () =>
    HttpResponse.json(combinationReview),
  ),
  http.post(api('/runs/:runName/constraints/combination/entries/:combinationId/counter-examples/generate'), () =>
    HttpResponse.json(combinationReview),
  ),
  http.put(api('/runs/:runName/constraints/combination/entries/:combinationId/counter-examples/:caseId'), () =>
    HttpResponse.json({
      ...combinationReview,
      cases: combinationReview.cases.map((item) => ({ ...item, case_state: 'APPROVED' })),
      review_state: 'APPROVED',
    }),
  ),
  http.post(api('/runs/:runName/constraints/combination/entries/:combinationId/counter-examples/run'), () =>
    HttpResponse.json({
      ...combinationReview,
      cases: combinationReview.cases.map((item) => ({
        ...item,
        case_state: 'EXECUTED',
        runtime_result: { response_status: 200 },
        runtime_verdict: 'BOTH_TRUE',
      })),
      review_state: 'RUN_COMPLETED',
      runtime_recommendation: 'INCONCLUSIVE',
    }),
  ),
  http.post(api('/runs/:runName/constraints/combination/entries/:combinationId/review/finalize'), () =>
    HttpResponse.json({
      ...combinationReview,
      decision_source: 'manual',
      has_manual_decision: true,
      manual_decision: 'ACCEPT_STATIC',
      rationale: 'Business owner accepted the static constraint.',
      review_state: 'FINAL_CONFIRMED',
    }),
  ),
  http.post(api('/runs/:runName/constraints/combination/entries/:combinationId/review/reopen'), () =>
    HttpResponse.json({ ...combinationReview, review_state: 'REOPENED' }),
  ),
  http.post(api('/runs/:runName/constraints/combination/counter-examples/batch-generate'), () =>
    HttpResponse.json({
      results: [
        {
          case_count: 1,
          combination_id: 'cmb-limit',
          message: 'Draft generated',
          new_case_count: 1,
          status: 'generated',
          total_case_count: 1,
        },
      ],
    }),
  ),
  http.get(api('/runs/:runName/constraints/combination/facets'), () => HttpResponse.json(combinationFacets)),
  http.get(api('/runs/:runName/constraints/research/summary'), () => HttpResponse.json(constraintResearchSummary)),
  http.get(api('/runs/:runName/constraints/research/entries'), () => HttpResponse.json(constraintResearchEntries)),
  http.get(api('/runs/:runName/constraints/research/entries/:combinationId'), () =>
    HttpResponse.json(constraintResearchDetail),
  ),
  http.put(api('/runs/:runName/constraints/research/entries/:combinationId/labels'), async ({ request }) => {
    const body = await request.json() as {
      combined_label?: string | null
      dynamic_label?: string
      notes?: string
      static_label?: string
    }
    return HttpResponse.json({
      ...constraintResearchEntries.items[0],
      combined_label: body.combined_label ?? null,
      dynamic_label: body.dynamic_label ?? constraintResearchEntries.items[0].dynamic_label,
      notes: body.notes ?? constraintResearchEntries.items[0].notes,
      static_label: body.static_label ?? constraintResearchEntries.items[0].static_label,
      updated_at: '2026-01-01T00:04:00Z',
    })
  }),
  http.get(api('/runs/:runName/constraints/research/labels.csv'), () =>
    HttpResponse.text('research_pair_id,run_name,combination_id,static_label,dynamic_label,combined_label,orphaned\nrp-static-stronger,Run A,cmb-static-stronger,TP,TP,UNSURE,false\n'),
  ),
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
