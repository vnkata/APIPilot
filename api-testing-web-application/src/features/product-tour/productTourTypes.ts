export type TourRole = 'qa-qc'

export type TourId =
  | 'app-shell'
  | 'runs'
  | 'overview'
  | 'operations'
  | 'graph'
  | 'constraints'
  | 'artifacts'
  | 'reports'
  | 'test-cases'
  | 'history'

export type TourAnchorId =
  | 'app-sidebar'
  | 'app-run-context'
  | 'app-density-control'
  | 'app-backend-health'
  | 'app-help'
  | 'runs-header'
  | 'runs-catalog'
  | 'overview-header'
  | 'overview-health-signals'
  | 'overview-next-inspection'
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

export type TourStepPlacement = 'auto' | 'bottom' | 'center' | 'left' | 'right' | 'top'

export type TourStepAction = {
  href?: string
  label: string
}

export type TourStep = {
  action?: TourStepAction
  anchorId: TourAnchorId
  body: string
  id: string
  placement?: TourStepPlacement
  title: string
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
