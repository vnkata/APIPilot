import type { TourDefinition, TourId } from './productTourTypes'

export type TourMeta = {
  id: TourId
  label: string
  routePattern: RegExp
}

const tourLoaders: Record<TourId, () => Promise<TourDefinition>> = {
  'app-shell': () => import('./tourDefinitions').then((module) => module.appShellTour),
  artifacts: () => import('./tourDefinitions').then((module) => module.artifactsTour),
  constraints: () => import('./tourDefinitions').then((module) => module.constraintsTour),
  graph: () => import('./tourDefinitions').then((module) => module.graphTour),
  history: () => import('./tourDefinitions').then((module) => module.historyTour),
  operations: () => import('./tourDefinitions').then((module) => module.operationsTour),
  overview: () => import('./tourDefinitions').then((module) => module.overviewTour),
  reports: () => import('./tourDefinitions').then((module) => module.reportsTour),
  runs: () => import('./tourDefinitions').then((module) => module.runsTour),
  'test-cases': () => import('./tourDefinitions').then((module) => module.testCasesTour),
}

export const tourMetas: TourMeta[] = [
  { id: 'app-shell', label: 'APIPilot workspace', routePattern: /^\/.*/ },
  { id: 'runs', label: 'Runs catalog', routePattern: /^\/runs\/?$/ },
  { id: 'overview', label: 'Run overview', routePattern: /^\/runs\/[^/]+\/?$/ },
  { id: 'operations', label: 'Operations', routePattern: /^\/runs\/[^/]+\/operations\/?$/ },
  { id: 'graph', label: 'Graph', routePattern: /^\/runs\/[^/]+\/graph\/?$/ },
  { id: 'constraints', label: 'Constraints', routePattern: /^\/runs\/[^/]+\/constraints\/?$/ },
  { id: 'artifacts', label: 'Artifacts', routePattern: /^\/runs\/[^/]+\/artifacts\/?$/ },
  { id: 'reports', label: 'Reports', routePattern: /^\/runs\/[^/]+\/reports\/?$/ },
  { id: 'test-cases', label: 'Test cases', routePattern: /^\/runs\/[^/]+\/test-cases\/?$/ },
  { id: 'history', label: 'History', routePattern: /^\/runs\/[^/]+\/history\/?$/ },
]

export function currentPageTourId(pathname: string): TourId | undefined {
  return tourMetas.find((meta) => meta.id !== 'app-shell' && meta.routePattern.test(pathname))?.id
}

export function availableTourIds(pathname: string): TourId[] {
  const pageTourId = currentPageTourId(pathname)
  return pageTourId ? ['app-shell', pageTourId] : ['app-shell']
}

export function tourLabel(tourId: TourId) {
  return tourMetas.find((meta) => meta.id === tourId)?.label ?? tourId
}

export function loadTourDefinition(tourId: TourId) {
  return tourLoaders[tourId]()
}
