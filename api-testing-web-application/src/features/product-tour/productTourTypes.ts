export type TourRole = 'qa-qc'

export type TourId =
  | 'app-shell'
  | 'onboarding'
  | 'runs'
  | 'overview'
  | 'workspace'
  | 'operations'
  | 'graph'
  | 'constraints-fundamentals'
  | 'constraints-workbench'
  | 'constraints-explorer'
  | 'artifacts'
  | 'reports'
  | 'test-cases'
  | 'history'
  | 'compare'
  | 'builder-specs'
  | 'builder-run-config'
  | 'builder-executions'
  | 'builder-execution-detail'

export type TourAnchorId =
  | 'app-sidebar'
  | 'app-run-context'
  | 'app-density-control'
  | 'app-backend-health'
  | 'app-help'
  | 'onboarding-paths'
  | 'runs-header'
  | 'runs-catalog'
  | 'overview-header'
  | 'overview-health-signals'
  | 'overview-next-inspection'
  | 'workspace-header'
  | 'workspace-operations'
  | 'workspace-graph-focus'
  | 'workspace-inspector'
  | 'workspace-evidence-tray'
  | 'operations-header'
  | 'operations-filters'
  | 'operations-results'
  | 'operations-detail'
  | 'graph-header'
  | 'graph-controls'
  | 'graph-results'
  | 'graph-inspector'
  | 'constraints-header'
  | 'constraints-filters'
  | 'constraints-workbench'
  | 'constraints-matrix'
  | 'constraints-detail'
  | 'constraints-learning-panel'
  | 'artifacts-header'
  | 'artifacts-catalog'
  | 'artifacts-detail'
  | 'reports-header'
  | 'reports-status-distribution'
  | 'reports-results'
  | 'test-cases-header'
  | 'test-cases-results'
  | 'test-cases-detail'
  | 'history-header'
  | 'history-sessions'
  | 'history-results'
  | 'history-detail'
  | 'compare-header'
  | 'compare-selectors'
  | 'compare-metadata-diff'
  | 'compare-content-diff'
  | 'compare-content-panels'
  | 'builder-specs-header'
  | 'builder-specs-catalog'
  | 'builder-specs-upload'
  | 'builder-spec-detail-header'
  | 'builder-spec-operations'
  | 'builder-run-config-header'
  | 'builder-run-config-summary'
  | 'builder-run-config-stepper'
  | 'builder-run-config-fields'
  | 'builder-run-config-actions'
  | 'builder-executions-header'
  | 'builder-executions-filters'
  | 'builder-executions-table'
  | 'builder-execution-header'
  | 'builder-execution-summary'
  | 'builder-execution-timeline'

export type TourStepPlacement = 'auto' | 'bottom' | 'center' | 'left' | 'right' | 'top'

export type TourStepAction = {
  href?: string
  label: string
}

export type TourStep = {
  action?: TourStepAction
  anchorId: TourAnchorId
  body: string
  bullets?: string[]
  domainTerm?: {
    definition: string
    term: string
  }
  id: string
  placement?: TourStepPlacement
  title: string
  whyItMatters?: string
}

export type TourDefinition = {
  description: string
  id: TourId
  label: string
  roles: TourRole[]
  steps: TourStep[]
  version: number
}

export type TourAnalyticsEvent =
  | {
      stepId?: string
      tourId: TourId
      type: 'prompt_shown' | 'tour_completed' | 'tour_skipped' | 'tour_started'
      version: number
    }
  | {
      stepId: string
      stepIndex: number
      tourId: TourId
      type: 'step_action_clicked' | 'step_viewed'
      version: number
    }

export type TourProgress = {
  completedVersion?: number
  dismissedVersion?: number
  lastStepIndex?: number
  skippedVersion?: number
}
