import type {
  CombinationDetailResponse,
  CombinationReviewResponse,
} from '../../shared/api/generated/model'
import {
  combinationHitlActivationVersion,
  combinationHitlActivationWorkflowId,
  type ActivationAnalyticsMetadata,
  type ActivationRunProgress,
  type ActivationStepState,
  type CombinationHitlActivationStepId,
} from './activationOnboardingTypes'

export type CombinationHitlActivationRoute = 'combination_table' | 'review_workspace'

export type CombinationHitlActivationStepDefinition = {
  description: string
  id: CombinationHitlActivationStepId
  label: string
}

export type CombinationHitlActivationStepModel = CombinationHitlActivationStepDefinition & {
  state: ActivationStepState
}

export type CombinationHitlActivationModel = {
  active: boolean
  completed: boolean
  completedCount: number
  dismissed: boolean
  nextAction: string
  steps: CombinationHitlActivationStepModel[]
  totalCount: number
}

export const combinationHitlActivationSteps: CombinationHitlActivationStepDefinition[] = [
  {
    description: 'Open the Combination table for the selected run.',
    id: 'open_combination_table',
    label: 'Open Combination table',
  },
  {
    description: 'Select a row that needs counter-example review.',
    id: 'select_eligible_row',
    label: 'Select eligible row',
  },
  {
    description: 'Open the selected row preview, then continue in the dedicated review workspace.',
    id: 'open_review_workspace',
    label: 'Open review workspace',
  },
  {
    description: 'Generate draft diagnostic counter-example cases.',
    id: 'generate_draft',
    label: 'Generate draft',
  },
  {
    description: 'Review and approve at least one executable draft case.',
    id: 'approve_case',
    label: 'Approve case',
  },
  {
    description: 'Run approved cases against an explicit safe target.',
    id: 'run_evidence',
    label: 'Run evidence',
  },
  {
    description: 'Finalize or reopen the human decision with rationale.',
    id: 'finalize_decision',
    label: 'Finalize decision',
  },
]

const enumValuePattern = /^[A-Z][A-Z0-9_]*$/

function safeEnumValue(value: string | null | undefined) {
  return value && enumValuePattern.test(value) ? value : undefined
}

function hasRuntimeEvidence(review?: CombinationReviewResponse) {
  return Boolean(
    review?.runtime_recommendation && review.runtime_recommendation !== 'NO_RECOMMENDATION',
  ) || Boolean(review?.cases.some((item) => item.runtime_result || item.runtime_verdict))
}

function isBackendStepComplete(
  stepId: CombinationHitlActivationStepId,
  input: {
    review?: CombinationReviewResponse
    route: CombinationHitlActivationRoute
    selectedEligibleCombinationCount?: number
  },
) {
  const { review, route, selectedEligibleCombinationCount = 0 } = input

  if (stepId === 'open_combination_table') return route === 'combination_table'
  if (stepId === 'select_eligible_row') return selectedEligibleCombinationCount > 0
  if (stepId === 'open_review_workspace') return route === 'review_workspace'
  if (stepId === 'generate_draft') {
    return Boolean(review?.cases.length)
      || ['DRAFT_READY', 'APPROVED', 'RUN_COMPLETED', 'FINAL_CONFIRMED'].includes(review?.review_state ?? '')
  }
  if (stepId === 'approve_case') {
    return Boolean(review?.cases.some((item) => item.case_state === 'APPROVED' || item.case_state === 'EXECUTED'))
      || ['APPROVED', 'RUN_COMPLETED', 'FINAL_CONFIRMED'].includes(review?.review_state ?? '')
  }
  if (stepId === 'run_evidence') {
    return hasRuntimeEvidence(review) || ['RUN_COMPLETED', 'FINAL_CONFIRMED'].includes(review?.review_state ?? '')
  }
  if (stepId === 'finalize_decision') {
    return Boolean(review?.has_manual_decision) || review?.review_state === 'FINAL_CONFIRMED'
  }
  return false
}

export function deriveCombinationHitlActivationModel(input: {
  detail?: CombinationDetailResponse
  progress?: ActivationRunProgress
  review?: CombinationReviewResponse
  route: CombinationHitlActivationRoute
  selectedEligibleCombinationCount?: number
}): CombinationHitlActivationModel {
  let firstPendingSeen = false
  const steps = combinationHitlActivationSteps.map((step) => {
    const completed = Boolean(input.progress?.completedStepIds[step.id])
      || isBackendStepComplete(step.id, input)
    const skipped = Boolean(input.progress?.skippedStepIds[step.id])
    const state: ActivationStepState = completed ? 'completed'
      : skipped ? 'skipped'
        : !firstPendingSeen ? 'current'
          : 'pending'
    if (state === 'current') firstPendingSeen = true
    return { ...step, state }
  })
  const completedCount = steps.filter((step) => step.state === 'completed').length
  const completed = steps.find((step) => step.id === 'finalize_decision')?.state === 'completed'
  const nextStep = steps.find((step) => step.state === 'current')

  return {
    active: Boolean(input.progress?.active),
    completed,
    completedCount,
    dismissed: Boolean(input.progress?.dismissed),
    nextAction: completed ? 'Activation complete.' : nextStep?.description ?? 'Review skipped steps when you are ready.',
    steps,
    totalCount: steps.length,
  }
}

export function safeCombinationActivationMetadata(input: {
  detail?: {
    relation?: string | null
    status?: string | null
  }
  review?: CombinationReviewResponse
}): ActivationAnalyticsMetadata {
  return {
    manualDecision: safeEnumValue(input.review?.manual_decision),
    relation: safeEnumValue(input.detail?.relation),
    reviewState: safeEnumValue(input.review?.review_state),
    status: safeEnumValue(input.detail?.status),
  }
}

export function combinationHitlActivationEventBase() {
  return {
    version: combinationHitlActivationVersion,
    workflowId: combinationHitlActivationWorkflowId,
  } as const
}
