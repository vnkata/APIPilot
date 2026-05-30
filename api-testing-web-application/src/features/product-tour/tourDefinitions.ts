import type { TourDefinition } from './productTourTypes'
import { TOUR_ANCHORS } from './tourAnchors'

export const appShellTour: TourDefinition = {
  description: 'Learn global navigation, run context, health, and Help controls.',
  id: 'app-shell',
  label: 'APIPilot workspace tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.appSidebar,
      body: 'Use the sidebar as your map. Start at Overview, then move into Operations, Constraints, Graph, Artifacts, Reports, Test cases, or History.',
      id: 'navigation',
      placement: 'right',
      title: 'Navigate by investigation job',
    },
    {
      anchorId: TOUR_ANCHORS.appRunContext,
      body: 'The top bar confirms the active run so you do not mix artifacts from different executions.',
      id: 'run-context',
      placement: 'bottom',
      title: 'Verify the run context',
    },
    {
      anchorId: TOUR_ANCHORS.appBackendHealth,
      body: 'Backend status tells you whether the read-only artifact API is reachable before you trust empty or stale screens.',
      id: 'backend-health',
      placement: 'bottom',
      title: 'Check artifact backend health',
    },
    {
      anchorId: TOUR_ANCHORS.appDensityControl,
      body: 'Toggle density when switching between scan-heavy tables and review-heavy detail work.',
      id: 'density',
      placement: 'bottom',
      title: 'Tune workspace density',
    },
    {
      anchorId: TOUR_ANCHORS.appHelp,
      body: 'Open Help any time to restart this tour or launch the tour for the current page.',
      id: 'help-menu',
      placement: 'bottom',
      title: 'Use contextual Help',
    },
  ],
}

export const runsTour: TourDefinition = {
  description: 'Choose a cached run and enter the artifact workspace.',
  id: 'runs',
  label: 'Runs catalog tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.runsHeader,
      body: 'Runs are read-only cache snapshots. Pick the run you want to inspect before drilling into generated artifacts.',
      id: 'runs-purpose',
      title: 'Start with a run snapshot',
    },
    {
      anchorId: TOUR_ANCHORS.runsCatalog,
      body: 'Each run card shows artifact count, size, modified time, and history availability. Open a run to inspect its workflow evidence.',
      id: 'runs-catalog',
      title: 'Select the right run',
    },
  ],
}

export const overviewTour: TourDefinition = {
  description: 'Use QA Mission Control for first-pass triage.',
  id: 'overview',
  label: 'Overview tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.overviewHeader,
      body: 'This is the triage surface for a single run. Use it to decide what needs inspection first.',
      id: 'overview-purpose',
      title: 'Begin with mission control',
    },
    {
      anchorId: TOUR_ANCHORS.overviewHealthSignals,
      body: 'Health signals combine failures, constraints, and available artifacts so you can spot risk quickly.',
      id: 'health-signals',
      title: 'Read the run signals',
    },
    {
      anchorId: TOUR_ANCHORS.overviewNextInspection,
      body: 'These links jump into the most useful next workspace without inventing a new workflow.',
      id: 'next-inspection',
      title: 'Follow the next best inspection',
    },
  ],
}

export const operationsTour: TourDefinition = {
  description: 'Triage operations by failures, evidence, and generated artifacts.',
  id: 'operations',
  label: 'Operations tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.operationsHeader,
      body: 'Switch between table, canvas, and cards depending on whether you need precision, evidence flow, or fast scanning.',
      id: 'operation-modes',
      title: 'Choose an operation view',
    },
    {
      anchorId: TOUR_ANCHORS.operationsFilters,
      body: 'Use search for text, then facet chips for failure, constraint, invariant, graph, and status signals.',
      id: 'operation-filters',
      title: 'Narrow the operation set',
    },
    {
      anchorId: TOUR_ANCHORS.operationsResults,
      body: 'Open an operation row to inspect linked constraints, reports, graph evidence, and test cases.',
      id: 'operation-results',
      title: 'Open evidence-rich details',
    },
  ],
}

export const graphTour: TourDefinition = {
  description: 'Understand operation dependency evidence and generated sequences.',
  id: 'graph',
  label: 'Graph tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.graphHeader,
      body: 'Graph mode helps you understand dependencies, edge evidence, nodes, and generated operation sequences.',
      id: 'graph-purpose',
      title: 'Read API behavior as a graph',
    },
    {
      anchorId: TOUR_ANCHORS.graphControls,
      body: 'Explorer is best for evidence tables, Journey for guided flows, and Spatial for visual inspection when the viewport supports it.',
      id: 'graph-controls',
      title: 'Choose the right graph lens',
    },
    {
      anchorId: TOUR_ANCHORS.graphResults,
      body: 'Use the result region to select edges, nodes, or sequences and open deeper evidence.',
      id: 'graph-results',
      title: 'Inspect graph evidence',
    },
  ],
}

export const constraintsTour: TourDefinition = {
  description: 'Find, prioritize, and inspect generated API oracle signals.',
  id: 'constraints',
  label: 'Constraints tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.constraintsHeader,
      body: 'Constraints and invariants are generated oracle candidates. Start in Workbench for triage, then use Explorer for precision.',
      id: 'constraints-purpose',
      title: 'Use constraints as oracle signals',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsFilters,
      body: 'Use the primary filters for common triage. Advanced filters stay in the drawer so the page remains scannable.',
      id: 'constraints-filters',
      title: 'Find signals without chip overload',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsWorkbench,
      body: 'Follow Find, Prioritize, Inspect. The ranked list surfaces assertion-ready and cross-source signals first.',
      id: 'constraints-workbench',
      title: 'Start with the guided workbench',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsMatrix,
      body: 'The matrix summarizes the current page only. Click a cell to jump into a filtered explorer view.',
      id: 'constraints-matrix',
      title: 'Use the readiness matrix',
      action: {
        href: '/runs/{runName}/constraints?constraintsView=table&constraintTab=explorer',
        label: 'Open Explorer',
      },
    },
  ],
}

export const artifactsTour: TourDefinition = {
  description: 'Inspect summaries, raw content, and compare views safely.',
  id: 'artifacts',
  label: 'Artifacts tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.artifactsHeader,
      body: 'Artifacts are read-only backend outputs. Use this workspace to inspect generated files without copying raw cache into Redux.',
      id: 'artifacts-purpose',
      title: 'Inspect generated artifacts',
    },
    {
      anchorId: TOUR_ANCHORS.artifactsCatalog,
      body: 'Search and filter the catalog by artifact kind or raw policy, then choose the artifact to inspect.',
      id: 'artifact-catalog',
      title: 'Choose an artifact',
    },
    {
      anchorId: TOUR_ANCHORS.artifactsDetail,
      body: 'Use Summary first. Raw and Compare are available when the backend marks raw content as safe and supported.',
      id: 'artifact-detail',
      title: 'Review content safely',
    },
  ],
}

export const reportsTour: TourDefinition = {
  description: 'Analyze status distribution and operation risk concentration.',
  id: 'reports',
  label: 'Reports tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.reportsHeader,
      body: 'Reports summarize response-status distribution and operation-level risk signals for the run.',
      id: 'reports-purpose',
      title: 'Use reports for risk concentration',
    },
    {
      anchorId: TOUR_ANCHORS.reportsStatusDistribution,
      body: 'The chart and table equivalent both show status distribution so visual and non-visual review stay aligned.',
      id: 'status-distribution',
      title: 'Read status distribution',
    },
    {
      anchorId: TOUR_ANCHORS.reportsResults,
      body: 'Filter the table by status or operation to move from aggregate risk to concrete endpoint evidence.',
      id: 'report-results',
      title: 'Drill into report rows',
    },
  ],
}

export const testCasesTour: TourDefinition = {
  description: 'Review generated sanitized test case examples.',
  id: 'test-cases',
  label: 'Test cases tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.testCasesHeader,
      body: 'Test cases show sanitized request/response examples linked to operations and artifact evidence.',
      id: 'test-cases-purpose',
      title: 'Review generated test cases',
    },
    {
      anchorId: TOUR_ANCHORS.testCasesResults,
      body: 'Open a row to inspect request and response fields. Body data remains opt-in and sanitized.',
      id: 'test-case-results',
      title: 'Inspect examples safely',
    },
  ],
}

export const historyTour: TourDefinition = {
  description: 'Inspect sanitized HAR sessions and request history.',
  id: 'history',
  label: 'History tour',
  roles: ['qa-qc'],
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.historyHeader,
      body: 'History shows captured HAR sessions and sanitized request/response entries for debugging run behavior.',
      id: 'history-purpose',
      title: 'Use HAR history for debugging',
    },
    {
      anchorId: TOUR_ANCHORS.historySessions,
      body: 'Select the session before reviewing entries so the table reflects the right capture context.',
      id: 'history-sessions',
      title: 'Choose a HAR session',
    },
    {
      anchorId: TOUR_ANCHORS.historyResults,
      body: 'Open an entry for headers, status, timing, and sanitized body context when available.',
      id: 'history-results',
      title: 'Open request history details',
    },
  ],
}
