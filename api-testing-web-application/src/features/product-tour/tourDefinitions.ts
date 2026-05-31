import type { TourDefinition, TourId, TourStep } from './productTourTypes'
import { TOUR_ANCHORS } from './tourAnchors'

const expandedTourVersion = 2

function defineTour(input: {
  description: string
  id: TourId
  label: string
  steps: TourStep[]
  version?: number
}): TourDefinition {
  return {
    description: input.description,
    id: input.id,
    label: input.label,
    roles: ['qa-qc'],
    steps: input.steps,
    version: input.version ?? expandedTourVersion,
  }
}

export const onboardingTour = defineTour({
  description: 'Choose the best first learning path for APIPilot.',
  id: 'onboarding',
  label: 'New to APIPilot',
  version: 1,
  steps: [
    {
      anchorId: TOUR_ANCHORS.onboardingPaths,
      body: 'Pick one path: inspect an existing run, build a new run from an OpenAPI spec, or compare evidence across two runs.',
      bullets: [
        'Investigation is best when artifacts already exist.',
        'Builder is best when you want APIPilot to create a dry-run execution.',
        'Compare is best when you need to explain what changed.',
      ],
      id: 'choose-path',
      title: 'Choose your first APIPilot path',
      whyItMatters: 'APIPilot has several expert workflows; starting with the right one makes the rest of the UI easier to understand.',
    },
  ],
})

export const appShellTour = defineTour({
  description: 'Learn global navigation, run context, health, command, and Help controls.',
  id: 'app-shell',
  label: 'APIPilot workspace',
  steps: [
    {
      anchorId: TOUR_ANCHORS.appSidebar,
      body: 'Use the sidebar as the product map. Builder creates runs, Investigation explains one run, and Compare analyzes deltas.',
      bullets: ['Builder is write-flow UI.', 'Investigation is read-only run inspection.', 'Compare is cross-run evidence review.'],
      id: 'navigation',
      placement: 'right',
      title: 'Navigate by product mode',
      whyItMatters: 'The mode boundary keeps you from mixing setup work with evidence review.',
    },
    {
      anchorId: TOUR_ANCHORS.appRunContext,
      body: 'The top bar confirms the active run and page context.',
      id: 'run-context',
      placement: 'bottom',
      title: 'Verify the run context',
    },
    {
      anchorId: TOUR_ANCHORS.appBackendHealth,
      body: 'Backend status tells you whether the artifact API is reachable before you interpret an empty view.',
      id: 'backend-health',
      placement: 'bottom',
      title: 'Check artifact backend health',
    },
    {
      anchorId: TOUR_ANCHORS.appDensityControl,
      body: 'Density changes table and panel spacing for scan-heavy or review-heavy desktop work.',
      id: 'density',
      placement: 'bottom',
      title: 'Tune workspace density',
    },
    {
      anchorId: TOUR_ANCHORS.appHelp,
      body: 'Help lists every guided tour available for the current route.',
      id: 'help-menu',
      placement: 'bottom',
      title: 'Use contextual Help',
    },
    {
      anchorId: TOUR_ANCHORS.appSidebar,
      body: 'Open Builder when you need to upload a spec, validate a run config, and start a dry-run execution.',
      id: 'builder-mode',
      placement: 'right',
      title: 'Builder creates new evidence',
    },
    {
      anchorId: TOUR_ANCHORS.appSidebar,
      body: 'Open Compare when you need a side-by-side artifact and metadata explanation.',
      id: 'compare-mode',
      placement: 'right',
      title: 'Compare explains deltas',
    },
  ],
})

export const runsTour = defineTour({
  description: 'Choose a cached run and enter the artifact workspace.',
  id: 'runs',
  label: 'Runs catalog tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.runsHeader,
      body: 'Runs are local artifact snapshots. Choose one before inspecting operations, constraints, graphs, reports, or history.',
      bullets: ['A run is read-only in Investigation.', 'Builder executions can later publish new runs.'],
      id: 'runs-purpose',
      title: 'Start with a run snapshot',
      whyItMatters: 'Every investigation page is scoped to a run, so choosing the right snapshot is the first safety check.',
    },
    {
      anchorId: TOUR_ANCHORS.runsCatalog,
      body: 'Cards summarize artifact count, size, modified time, and history availability.',
      id: 'runs-catalog',
      title: 'Select the right run',
    },
    {
      anchorId: TOUR_ANCHORS.runsCatalog,
      body: 'Open the run with the evidence you want to explain, then use Overview for first-pass triage.',
      id: 'runs-next',
      title: 'Open Overview first',
    },
  ],
})

export const overviewTour = defineTour({
  description: 'Use QA Mission Control for first-pass triage.',
  id: 'overview',
  label: 'Overview tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.overviewHeader,
      body: 'Overview is the front door for one run. It tells you what deserves attention before you open dense tables.',
      id: 'overview-purpose',
      title: 'Begin with mission control',
      whyItMatters: 'This page prevents random drilling and keeps investigation focused.',
    },
    {
      anchorId: TOUR_ANCHORS.overviewHealthSignals,
      body: 'Health signals combine operation failures, constraints, reports, and artifact availability.',
      bullets: ['Failures point to execution risk.', 'Constraints point to oracle potential.', 'Artifacts point to available evidence.'],
      id: 'health-signals',
      title: 'Read the run signals',
    },
    {
      anchorId: TOUR_ANCHORS.overviewNextInspection,
      body: 'Next inspection links jump to the most useful page for the current run state.',
      id: 'next-inspection',
      title: 'Follow the next best action',
    },
    {
      anchorId: TOUR_ANCHORS.overviewNextInspection,
      body: 'Use Workspace when you need operations, graph evidence, notes, and bookmarks in one desktop layout.',
      id: 'workspace-entry',
      title: 'Move into Workspace for investigation',
    },
  ],
})

export const workspaceTour = defineTour({
  description: 'Use the desktop investigation cockpit.',
  id: 'workspace',
  label: 'Workspace tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.workspaceHeader,
      body: 'Workspace combines operations, graph evidence, an inspector, saved views, bookmarks, and local notes.',
      bullets: ['URL state preserves current selection.', 'Local storage keeps views, notes, and bookmarks in this browser.'],
      id: 'workspace-purpose',
      title: 'Use Workspace as the investigation cockpit',
      whyItMatters: 'Desktop QA work is faster when evidence stays visible instead of scattered across pages.',
    },
    {
      anchorId: TOUR_ANCHORS.workspaceHeader,
      body: 'Layout presets let you shift space toward tables, graph evidence, or inspector review.',
      id: 'layout-presets',
      title: 'Choose a layout preset',
    },
    {
      anchorId: TOUR_ANCHORS.workspaceOperations,
      body: 'The operations pane is the primary triage list. Search and sort here before opening detail.',
      id: 'operations-pane',
      title: 'Start from operations',
    },
    {
      anchorId: TOUR_ANCHORS.workspaceGraphFocus,
      body: 'Graph focus surfaces dependency edges without loading the full graph workspace.',
      id: 'graph-focus',
      title: 'Inspect dependency evidence quickly',
    },
    {
      anchorId: TOUR_ANCHORS.workspaceInspector,
      body: 'The inspector explains the selected operation, edge, or sequence and stores local notes.',
      id: 'inspector',
      title: 'Keep context in the inspector',
    },
    {
      anchorId: TOUR_ANCHORS.workspaceEvidenceTray,
      body: 'Pinned evidence and recent activity keep your trail visible during long investigations.',
      id: 'pinned-evidence',
      title: 'Pin evidence you will revisit',
    },
  ],
})

export const operationsTour = defineTour({
  description: 'Triage operations by failures, evidence, and generated artifacts.',
  id: 'operations',
  label: 'Operations tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.operationsHeader,
      body: 'Operations are the API endpoints APIPilot exercised or inspected for the run.',
      domainTerm: {
        definition: 'A single OpenAPI method and path pair, enriched with observed execution and generated evidence.',
        term: 'Operation',
      },
      id: 'operation-modes',
      title: 'Read one endpoint at a time',
      whyItMatters: 'Most evidence, constraints, graph edges, reports, and test cases connect back to operations.',
    },
    {
      anchorId: TOUR_ANCHORS.operationsFilters,
      body: 'Search by text, then add facets for failure, constraint, invariant, graph, and status signals.',
      id: 'operation-filters',
      title: 'Narrow the operation set',
    },
    {
      anchorId: TOUR_ANCHORS.operationsResults,
      body: 'Rows are evidence entry points. Open one to inspect linked artifacts without leaving the current route.',
      id: 'operation-results',
      title: 'Open evidence-rich details',
    },
    {
      anchorId: TOUR_ANCHORS.operationsDetail,
      body: 'Operation detail connects the selected endpoint to constraints, graph evidence, reports, and test cases.',
      id: 'operation-detail',
      title: 'Use detail as the evidence hub',
    },
  ],
})

export const graphTour = defineTour({
  description: 'Understand operation dependency evidence and generated sequences.',
  id: 'graph',
  label: 'Graph tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.graphHeader,
      body: 'Graph mode explains dependencies, evidence edges, nodes, and generated operation sequences.',
      domainTerm: {
        definition: 'A directed relationship where one operation provides data or state used by another operation.',
        term: 'Dependency edge',
      },
      id: 'graph-purpose',
      title: 'Read API behavior as a graph',
      whyItMatters: 'Stateful API testing depends on knowing which operation can unlock another.',
    },
    {
      anchorId: TOUR_ANCHORS.graphControls,
      body: 'Explorer is best for evidence tables, Journey for guided flows, and Spatial for visual inspection.',
      bullets: ['Use Journey when Spatial appears sparse.', 'Use Explorer when you need exact edge evidence.'],
      id: 'graph-controls',
      title: 'Choose the right graph lens',
    },
    {
      anchorId: TOUR_ANCHORS.graphResults,
      body: 'Select edges, nodes, or sequences from the result region.',
      id: 'graph-results',
      title: 'Inspect graph evidence',
    },
    {
      anchorId: TOUR_ANCHORS.graphInspector,
      body: 'The inspector shows selected graph context and links back to operation evidence.',
      id: 'graph-inspector',
      title: 'Use inspector context',
    },
  ],
})

export const constraintsFundamentalsTour = defineTour({
  description: 'Learn the vocabulary behind generated API oracle signals.',
  id: 'constraints-fundamentals',
  label: 'Constraints tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.constraintsHeader,
      body: 'Constraints and invariants are generated oracle candidates, not automatically final test truth.',
      bullets: ['Use source to understand origin.', 'Use agreement to compare evidence.', 'Use assertion readiness to decide if it can become executable.'],
      domainTerm: {
        definition: 'A generated rule candidate that may become executable test logic after enough evidence is available.',
        term: 'Oracle signal',
      },
      id: 'constraints-purpose',
      title: 'Read constraints as oracle candidates',
      whyItMatters: 'This prevents treating every mined expression as equally reliable.',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsLearningPanel,
      body: 'Source tells whether the signal came from static mining, dynamic observations, or combined evidence.',
      id: 'source-signal',
      title: 'Source is your first trust signal',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsFilters,
      body: 'Agreement tells whether static and dynamic evidence align, conflict, or only exists on one side.',
      id: 'agreement-signal',
      title: 'Agreement explains confidence',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsFilters,
      body: 'Assertion availability means APIPilot has enough shape to turn a signal into an executable check.',
      id: 'assertion-signal',
      title: 'Assertion means executable potential',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsWorkbench,
      body: 'Oracle readiness ranks runtime invariants by whether they look usable as test oracles.',
      id: 'readiness-signal',
      title: 'Readiness ranks next action',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsMatrix,
      body: 'The matrix summarizes the currently loaded page, so treat it as a triage lens, not a global count.',
      id: 'matrix-signal',
      title: 'Matrix is a page-level summary',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsDetail,
      body: 'Open detail before exporting or turning a signal into a test. Detail shows expression, evidence, raw fields, and linked pages.',
      id: 'detail-signal',
      title: 'Verify detail before acting',
    },
  ],
})

export const constraintsWorkbenchTour = defineTour({
  description: 'Use the guided constraint workbench to prioritize risky signals.',
  id: 'constraints-workbench',
  label: 'Constraints workbench',
  steps: [
    {
      anchorId: TOUR_ANCHORS.constraintsWorkbench,
      body: 'Workbench is optimized for the Find, Prioritize, Inspect loop.',
      bullets: ['Find candidates with search and facets.', 'Prioritize ready and cross-source evidence.', 'Inspect detail before exporting.'],
      id: 'workbench-loop',
      title: 'Use Find, Prioritize, Inspect',
      whyItMatters: 'The workbench turns a dense constraint table into a repeatable triage workflow.',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsWorkbench,
      body: 'Top signals emphasize assertion-ready constraints and correlated invariants.',
      id: 'top-signals',
      title: 'Start with top signals',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsFilters,
      body: 'Primary filters keep common triage visible; deeper grouping and facets stay in Advanced filters.',
      id: 'filters',
      title: 'Filter without losing context',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsMatrix,
      body: 'Click a matrix cell to jump into a filtered Explorer view.',
      action: {
        href: '/runs/{runName}/constraints?constraintsView=table&constraintTab=explorer',
        label: 'Open Explorer',
      },
      id: 'matrix-action',
      title: 'Use matrix cells as shortcuts',
    },
  ],
})

export const constraintsExplorerTour = defineTour({
  description: 'Use Explorer and detail drawers for precise constraint review.',
  id: 'constraints-explorer',
  label: 'Constraints explorer',
  steps: [
    {
      anchorId: TOUR_ANCHORS.constraintsFilters,
      body: 'Explorer mode is for exact filtering, sorting, grouping, and detail review.',
      id: 'explorer-purpose',
      title: 'Use Explorer for precision',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsMatrix,
      body: 'Switch matrix grouping by source, kind, readiness, or agreement when you need a different mental model.',
      id: 'matrix-grouping',
      title: 'Change the matrix lens',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsDetail,
      body: 'Detail drawers explain one signal and expose evidence links to Graph, Reports, and Test cases.',
      id: 'detail-drawer',
      title: 'Open one signal at a time',
    },
    {
      anchorId: TOUR_ANCHORS.constraintsDetail,
      body: 'Raw fields are debugging aids. Prefer readable detail for first-pass interpretation.',
      id: 'raw-fields',
      title: 'Use raw fields deliberately',
    },
  ],
})

export const artifactsTour = defineTour({
  description: 'Inspect summaries, raw content, compare views, and export behavior safely.',
  id: 'artifacts',
  label: 'Artifacts tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.artifactsHeader,
      body: 'Artifacts are backend-generated outputs surfaced through a safe frontend API boundary.',
      id: 'artifacts-purpose',
      title: 'Inspect generated artifacts',
      whyItMatters: 'The frontend should never read local cache artifacts directly.',
    },
    {
      anchorId: TOUR_ANCHORS.artifactsCatalog,
      body: 'Search and filter the catalog by artifact kind, media type, and raw-content policy.',
      id: 'artifact-catalog',
      title: 'Choose an artifact',
    },
    {
      anchorId: TOUR_ANCHORS.artifactsDetail,
      body: 'Use Summary first. Raw content is opt-in and depends on backend safety policy.',
      id: 'artifact-detail',
      title: 'Review content safely',
    },
    {
      anchorId: TOUR_ANCHORS.artifactsDetail,
      body: 'Compare mode helps explain artifact deltas without opening a separate tool.',
      id: 'artifact-compare',
      title: 'Compare when evidence changed',
    },
  ],
})

export const reportsTour = defineTour({
  description: 'Analyze status distribution and operation risk concentration.',
  id: 'reports',
  label: 'Reports tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.reportsHeader,
      body: 'Reports summarize status distribution and operation-level risk for the run.',
      id: 'reports-purpose',
      title: 'Use reports for risk concentration',
    },
    {
      anchorId: TOUR_ANCHORS.reportsStatusDistribution,
      body: 'The chart and table-equivalent summary keep visual and non-visual review aligned.',
      id: 'status-distribution',
      title: 'Read status distribution',
    },
    {
      anchorId: TOUR_ANCHORS.reportsResults,
      body: 'Filter by status or operation to move from aggregate risk to endpoint evidence.',
      id: 'report-results',
      title: 'Drill into report rows',
    },
  ],
})

export const testCasesTour = defineTour({
  description: 'Review generated sanitized test case examples.',
  id: 'test-cases',
  label: 'Test cases tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.testCasesHeader,
      body: 'Test cases show sanitized request and response examples linked to operations.',
      id: 'test-cases-purpose',
      title: 'Review generated examples',
      whyItMatters: 'Examples are useful for debugging generated behavior but should remain sanitized.',
    },
    {
      anchorId: TOUR_ANCHORS.testCasesResults,
      body: 'Open a row to inspect request and response fields.',
      id: 'test-case-results',
      title: 'Inspect examples safely',
    },
    {
      anchorId: TOUR_ANCHORS.testCasesDetail,
      body: 'Body data remains opt-in and should be treated as sensitive debugging context.',
      id: 'test-case-detail',
      title: 'Treat bodies carefully',
    },
  ],
})

export const historyTour = defineTour({
  description: 'Inspect sanitized HAR sessions and request history.',
  id: 'history',
  label: 'History tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.historyHeader,
      body: 'History shows captured HAR sessions and sanitized request/response entries.',
      id: 'history-purpose',
      title: 'Use HAR history for debugging',
    },
    {
      anchorId: TOUR_ANCHORS.historySessions,
      body: 'Select the session first so the entries table reflects the right capture context.',
      id: 'history-sessions',
      title: 'Choose a HAR session',
    },
    {
      anchorId: TOUR_ANCHORS.historyResults,
      body: 'Open an entry for headers, status, timing, and sanitized body context.',
      id: 'history-results',
      title: 'Open request history details',
    },
    {
      anchorId: TOUR_ANCHORS.historyDetail,
      body: 'Detail is where you confirm request context before tying history back to operations.',
      id: 'history-detail',
      title: 'Use detail for request context',
    },
  ],
})

export const compareTour = defineTour({
  description: 'Compare run summaries, artifact metadata, and JSON-like content.',
  id: 'compare',
  label: 'Compare Lab tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.compareHeader,
      body: 'Compare Lab explains differences between two runs using only existing run and artifact APIs.',
      bullets: ['Metadata diff explains presence and policy changes.', 'JSON structural diff explains path-level content changes.'],
      id: 'compare-purpose',
      title: 'Use Compare for evidence deltas',
      whyItMatters: 'Side-by-side review helps distinguish real behavior changes from artifact availability changes.',
    },
    {
      anchorId: TOUR_ANCHORS.compareSelectors,
      body: 'Choose left run, right run, and artifact. The artifact list is built from both sides.',
      id: 'compare-selectors',
      title: 'Pick comparable evidence',
    },
    {
      anchorId: TOUR_ANCHORS.compareSelectors,
      body: 'Raw content is opt-in. Use structural JSON mode first when possible.',
      id: 'raw-toggle',
      title: 'Request raw content deliberately',
    },
    {
      anchorId: TOUR_ANCHORS.compareMetadataDiff,
      body: 'Metadata diff shows missing artifacts, size changes, media type changes, and raw policy changes.',
      id: 'metadata-diff',
      title: 'Read metadata before content',
    },
    {
      anchorId: TOUR_ANCHORS.compareContentDiff,
      body: 'Structural diff groups added, removed, and changed JSON-like paths.',
      id: 'content-diff',
      title: 'Inspect path-level changes',
    },
    {
      anchorId: TOUR_ANCHORS.compareContentPanels,
      body: 'Content panels show each side so you can verify a highlighted diff in context.',
      id: 'content-panels',
      title: 'Verify both sides',
    },
  ],
})

export const builderSpecsTour = defineTour({
  description: 'Upload OpenAPI specs and preview operations.',
  id: 'builder-specs',
  label: 'Spec Manager tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.builderSpecsHeader,
      body: 'Spec Manager is the Builder entry point. Upload OpenAPI JSON or YAML here before creating a run config.',
      id: 'specs-purpose',
      title: 'Start Builder with a spec',
      whyItMatters: 'Run configs should be based on a backend-validated spec, not copied UI assumptions.',
    },
    {
      anchorId: TOUR_ANCHORS.builderSpecsUpload,
      body: 'Upload reads the file as text and sends filename, content, and optional title to the backend.',
      id: 'spec-upload',
      title: 'Upload OpenAPI content',
    },
    {
      anchorId: TOUR_ANCHORS.builderSpecsCatalog,
      body: 'The catalog lists uploaded specs and operation counts so you can choose the right source.',
      id: 'spec-catalog',
      title: 'Choose from the spec catalog',
    },
    {
      anchorId: TOUR_ANCHORS.builderSpecOperations,
      body: 'Spec preview confirms operation IDs, methods, paths, request bodies, and response statuses.',
      id: 'spec-preview',
      title: 'Preview operations before configuring',
    },
  ],
})

export const builderRunConfigTour = defineTour({
  description: 'Create, validate, and optionally run APIPilot run configs.',
  id: 'builder-run-config',
  label: 'Run Config Builder tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.builderRunConfigHeader,
      body: 'Run Config Builder turns an uploaded spec into a validated APIPilot execution plan.',
      domainTerm: {
        definition: 'A saved set of generation, timeout, budget, AI, header, and execution-mode settings.',
        term: 'Run config',
      },
      id: 'run-config-purpose',
      title: 'Build an execution plan',
      whyItMatters: 'Validation catches missing or risky config before execution starts.',
    },
    {
      anchorId: TOUR_ANCHORS.builderRunConfigSummary,
      body: 'The summary shows mode, validation status, budget, timeout, and selected spec while you edit.',
      id: 'summary',
      title: 'Watch the config summary',
    },
    {
      anchorId: TOUR_ANCHORS.builderRunConfigStepper,
      body: 'The stepper communicates the intended order: spec, basics, AI, headers, then validation.',
      id: 'stepper',
      title: 'Follow the wizard order',
    },
    {
      anchorId: TOUR_ANCHORS.builderRunConfigFields,
      body: 'Basic fields define name, base URL, request budget, and timeout.',
      id: 'basic-fields',
      title: 'Set the execution boundary',
    },
    {
      anchorId: TOUR_ANCHORS.builderRunConfigFields,
      body: 'AI and embedding settings are optional and should use environment variable references for sensitive values.',
      id: 'ai-fields',
      title: 'Keep AI settings explicit',
    },
    {
      anchorId: TOUR_ANCHORS.builderRunConfigFields,
      body: 'Sensitive headers default to env refs. Do not persist raw tokens, cookies, or API keys.',
      id: 'headers',
      title: 'Protect secret-bearing headers',
    },
    {
      anchorId: TOUR_ANCHORS.builderRunConfigActions,
      body: 'Validate before create. Dry-run is deterministic; live execution requires explicit confirmation.',
      id: 'actions',
      title: 'Validate before execution',
      whyItMatters: 'Live mode can send requests to a configured target, so the UI keeps that path guarded.',
    },
  ],
})

export const builderExecutionsTour = defineTour({
  description: 'Track execution queue status, cancellation, and generated run entry points.',
  id: 'builder-executions',
  label: 'Execution Center tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.builderExecutionsHeader,
      body: 'Execution Center tracks dry-run and live executions created by Builder.',
      id: 'executions-purpose',
      title: 'Track Builder executions',
      whyItMatters: 'Execution status tells you whether a generated run is ready for Investigation.',
    },
    {
      anchorId: TOUR_ANCHORS.builderExecutionsFilters,
      body: 'Filter by status or mode when the queue grows.',
      id: 'execution-filters',
      title: 'Filter active and terminal work',
    },
    {
      anchorId: TOUR_ANCHORS.builderExecutionsTable,
      body: 'Rows open detail, cancel active executions, or jump to the generated run when available.',
      id: 'execution-table',
      title: 'Use row actions',
    },
  ],
})

export const builderExecutionDetailTour = defineTour({
  description: 'Review one execution timeline and open the generated run.',
  id: 'builder-execution-detail',
  label: 'Execution detail tour',
  steps: [
    {
      anchorId: TOUR_ANCHORS.builderExecutionHeader,
      body: 'Execution detail shows one run attempt, its current status, and generated-run CTA when published.',
      id: 'execution-detail-purpose',
      title: 'Inspect one execution',
    },
    {
      anchorId: TOUR_ANCHORS.builderExecutionSummary,
      body: 'Summary metadata is sanitized before display so debugging context does not expose raw secrets.',
      id: 'execution-summary',
      title: 'Review sanitized summary',
    },
    {
      anchorId: TOUR_ANCHORS.builderExecutionTimeline,
      body: 'The event timeline explains phases, status changes, messages, and sanitized metadata.',
      id: 'execution-timeline',
      title: 'Read the event timeline',
    },
  ],
})
