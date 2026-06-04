export const combinationHitlActivationWorkflowId = 'combination-hitl'
export const combinationHitlActivationVersion = 1

export type CombinationHitlActivationWorkflowId = typeof combinationHitlActivationWorkflowId

export type CombinationHitlActivationStepId =
  | 'approve_case'
  | 'finalize_decision'
  | 'generate_draft'
  | 'open_combination_table'
  | 'open_review_workspace'
  | 'run_evidence'
  | 'select_eligible_row'

export type ActivationStepState = 'completed' | 'current' | 'pending' | 'skipped'

export type ActivationStepProgress = Partial<Record<CombinationHitlActivationStepId, true>>

export type ActivationRunProgress = {
  active: boolean
  completedAt?: string
  completedStepIds: ActivationStepProgress
  dismissed: boolean
  skippedStepIds: ActivationStepProgress
}

export type ActivationOnboardingPersistedState = {
  progressByRunName: Record<string, ActivationRunProgress>
}

export type ActivationOnboardingState = ActivationOnboardingPersistedState

export type ActivationAnalyticsMetadata = {
  manualDecision?: string
  relation?: string
  reviewState?: string
  status?: string
}

export type ActivationOnboardingEvent =
  | {
      metadata?: ActivationAnalyticsMetadata
      stepId?: CombinationHitlActivationStepId
      type: 'activation_completed' | 'checklist_dismissed' | 'onboarding_started'
      version: number
      workflowId: CombinationHitlActivationWorkflowId
    }
  | {
      metadata?: ActivationAnalyticsMetadata
      stepId: CombinationHitlActivationStepId
      type: 'step_completed' | 'step_skipped'
      version: number
      workflowId: CombinationHitlActivationWorkflowId
    }
