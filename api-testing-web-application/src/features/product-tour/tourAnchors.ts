import type { TourAnchorId } from './productTourTypes'

export const TOUR_ANCHORS = {
  appBackendHealth: 'app-backend-health',
  appDensityControl: 'app-density-control',
  appHelp: 'app-help',
  appRunContext: 'app-run-context',
  appSidebar: 'app-sidebar',
  artifactsCatalog: 'artifacts-catalog',
  artifactsDetail: 'artifacts-detail',
  artifactsHeader: 'artifacts-header',
  constraintsDetail: 'constraints-detail',
  constraintsFilters: 'constraints-filters',
  constraintsHeader: 'constraints-header',
  constraintsMatrix: 'constraints-matrix',
  constraintsWorkbench: 'constraints-workbench',
  graphControls: 'graph-controls',
  graphHeader: 'graph-header',
  graphInspector: 'graph-inspector',
  graphResults: 'graph-results',
  historyDetail: 'history-detail',
  historyHeader: 'history-header',
  historyResults: 'history-results',
  historySessions: 'history-sessions',
  operationsDetail: 'operations-detail',
  operationsFilters: 'operations-filters',
  operationsHeader: 'operations-header',
  operationsResults: 'operations-results',
  overviewHeader: 'overview-header',
  overviewHealthSignals: 'overview-health-signals',
  overviewNextInspection: 'overview-next-inspection',
  reportsHeader: 'reports-header',
  reportsResults: 'reports-results',
  reportsStatusDistribution: 'reports-status-distribution',
  runsCatalog: 'runs-catalog',
  runsHeader: 'runs-header',
  testCasesDetail: 'test-cases-detail',
  testCasesHeader: 'test-cases-header',
  testCasesResults: 'test-cases-results',
} as const satisfies Record<string, TourAnchorId>

export function tourAnchor(anchorId: TourAnchorId) {
  return { 'data-tour-anchor': anchorId }
}
