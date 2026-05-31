import type { TourDefinition, TourId } from './productTourTypes'

export type TourMeta = {
  id: TourId
  label: string
  routePattern: RegExp
}

const tourLoaders: Record<TourId, () => Promise<TourDefinition>> = {
  'app-shell': () => import('./tourDefinitions').then((module) => module.appShellTour),
  artifacts: () => import('./tourDefinitions').then((module) => module.artifactsTour),
  'builder-execution-detail': () => import('./tourDefinitions').then((module) => module.builderExecutionDetailTour),
  'builder-executions': () => import('./tourDefinitions').then((module) => module.builderExecutionsTour),
  'builder-run-config': () => import('./tourDefinitions').then((module) => module.builderRunConfigTour),
  'builder-specs': () => import('./tourDefinitions').then((module) => module.builderSpecsTour),
  compare: () => import('./tourDefinitions').then((module) => module.compareTour),
  'constraints-explorer': () => import('./tourDefinitions').then((module) => module.constraintsExplorerTour),
  'constraints-fundamentals': () => import('./tourDefinitions').then((module) => module.constraintsFundamentalsTour),
  'constraints-workbench': () => import('./tourDefinitions').then((module) => module.constraintsWorkbenchTour),
  graph: () => import('./tourDefinitions').then((module) => module.graphTour),
  history: () => import('./tourDefinitions').then((module) => module.historyTour),
  onboarding: () => import('./tourDefinitions').then((module) => module.onboardingTour),
  operations: () => import('./tourDefinitions').then((module) => module.operationsTour),
  overview: () => import('./tourDefinitions').then((module) => module.overviewTour),
  reports: () => import('./tourDefinitions').then((module) => module.reportsTour),
  runs: () => import('./tourDefinitions').then((module) => module.runsTour),
  'test-cases': () => import('./tourDefinitions').then((module) => module.testCasesTour),
  workspace: () => import('./tourDefinitions').then((module) => module.workspaceTour),
}

export const tourMetas: TourMeta[] = [
  { id: 'app-shell', label: 'APIPilot workspace', routePattern: /^\/.*/ },
  { id: 'onboarding', label: 'New to APIPilot', routePattern: /^\/runs\/?$/ },
  { id: 'runs', label: 'Runs catalog', routePattern: /^\/runs\/?$/ },
  { id: 'overview', label: 'Run overview', routePattern: /^\/runs\/[^/]+\/?$/ },
  { id: 'workspace', label: 'Workspace', routePattern: /^\/runs\/[^/]+\/workspace\/?$/ },
  { id: 'operations', label: 'Operations', routePattern: /^\/runs\/[^/]+\/operations\/?$/ },
  { id: 'graph', label: 'Graph', routePattern: /^\/runs\/[^/]+\/graph\/?$/ },
  { id: 'constraints-fundamentals', label: 'Constraints fundamentals', routePattern: /^\/runs\/[^/]+\/constraints\/?$/ },
  { id: 'constraints-workbench', label: 'Constraints workbench', routePattern: /^\/runs\/[^/]+\/constraints\/?$/ },
  { id: 'constraints-explorer', label: 'Constraints explorer', routePattern: /^\/runs\/[^/]+\/constraints\/?$/ },
  { id: 'artifacts', label: 'Artifacts', routePattern: /^\/runs\/[^/]+\/artifacts\/?$/ },
  { id: 'reports', label: 'Reports', routePattern: /^\/runs\/[^/]+\/reports\/?$/ },
  { id: 'test-cases', label: 'Test cases', routePattern: /^\/runs\/[^/]+\/test-cases\/?$/ },
  { id: 'history', label: 'History', routePattern: /^\/runs\/[^/]+\/history\/?$/ },
  { id: 'compare', label: 'Compare Lab', routePattern: /^\/compare\/?$/ },
  { id: 'builder-specs', label: 'Spec Manager', routePattern: /^\/builder\/specs(?:\/[^/]+)?\/?$/ },
  { id: 'builder-run-config', label: 'Run Config Builder', routePattern: /^\/builder\/run-configs\/new\/?$/ },
  { id: 'builder-executions', label: 'Execution Center', routePattern: /^\/builder\/executions\/?$/ },
  { id: 'builder-execution-detail', label: 'Execution detail', routePattern: /^\/builder\/executions\/[^/]+\/?$/ },
]

export function currentPageTourId(pathname: string): TourId | undefined {
  return tourMetas.find((meta) => meta.id !== 'app-shell' && meta.id !== 'onboarding' && meta.routePattern.test(pathname))?.id
}

export function availableTourIds(pathname: string): TourId[] {
  const pageTourIds = tourMetas
    .filter((meta) => meta.id !== 'app-shell' && meta.id !== 'onboarding' && meta.routePattern.test(pathname))
    .map((meta) => meta.id)
  return ['app-shell', ...pageTourIds]
}

export function tourLabel(tourId: TourId) {
  return tourMetas.find((meta) => meta.id === tourId)?.label ?? tourId
}

export function loadTourDefinition(tourId: TourId) {
  return tourLoaders[tourId]()
}
