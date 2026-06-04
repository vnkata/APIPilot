import { describe, expect, it } from 'vitest'

import {
  combinationHitlActivationSteps,
  deriveCombinationHitlActivationModel,
  safeCombinationActivationMetadata,
} from './activationOnboardingViewModels'
import { combinationDetail, combinationReview, combinationReviewFinalConfirmed, combinationReviewWithRunnableAndEvidence } from '../../test/fixtures'

describe('activationOnboardingViewModels', () => {
  it('derives backend-state completion for the Combination HITL checklist', () => {
    const model = deriveCombinationHitlActivationModel({
      detail: combinationDetail,
      progress: {
        active: true,
        completedStepIds: {},
        dismissed: false,
        skippedStepIds: {},
      },
      review: combinationReviewWithRunnableAndEvidence,
      route: 'review_workspace',
      selectedEligibleCombinationCount: 0,
    })

    expect(model.steps.find((step) => step.id === 'open_review_workspace')?.state).toBe('completed')
    expect(model.steps.find((step) => step.id === 'generate_draft')?.state).toBe('completed')
    expect(model.steps.find((step) => step.id === 'approve_case')?.state).toBe('completed')
    expect(model.steps.find((step) => step.id === 'run_evidence')?.state).toBe('completed')
    expect(model.steps.find((step) => step.id === 'finalize_decision')?.state).toBe('pending')
    expect(model.completedCount).toBe(4)
    expect(model.totalCount).toBe(combinationHitlActivationSteps.length)
  })

  it('treats FINAL_CONFIRMED as activation completion', () => {
    const model = deriveCombinationHitlActivationModel({
      detail: combinationDetail,
      progress: {
        active: true,
        completedStepIds: {},
        dismissed: false,
        skippedStepIds: {},
      },
      review: combinationReviewFinalConfirmed,
      route: 'review_workspace',
      selectedEligibleCombinationCount: 0,
    })

    expect(model.completed).toBe(true)
    expect(model.steps.at(-1)?.id).toBe('finalize_decision')
    expect(model.steps.at(-1)?.state).toBe('completed')
  })

  it('does not erase persisted completion when a review has been reopened', () => {
    const model = deriveCombinationHitlActivationModel({
      detail: combinationDetail,
      progress: {
        active: true,
        completedStepIds: { finalize_decision: true },
        dismissed: false,
        skippedStepIds: {},
      },
      review: {
        ...combinationReview,
        review_state: 'REOPENED',
      },
      route: 'review_workspace',
      selectedEligibleCombinationCount: 0,
    })

    expect(model.steps.find((step) => step.id === 'finalize_decision')?.state).toBe('completed')
    expect(model.completed).toBe(true)
  })

  it('builds analytics metadata from safe enum-like values only', () => {
    const detailWithSensitiveFields = {
      ...combinationDetail,
      combination_id: 'cmb-secret',
      final_constraint: 'response.secret == "do-not-send"',
      operation_id: 'get-/private',
      property_path: 'response.secret',
      relation: 'DISJOINT',
      status: 'CONFLICT',
    }
    const metadata = safeCombinationActivationMetadata({
      detail: detailWithSensitiveFields,
      review: {
        ...combinationReview,
        manual_decision: 'ACCEPT_STATIC',
        review_state: 'FINAL_CONFIRMED',
      },
    })

    expect(metadata).toEqual({
      manualDecision: 'ACCEPT_STATIC',
      relation: 'DISJOINT',
      reviewState: 'FINAL_CONFIRMED',
      status: 'CONFLICT',
    })
    expect(JSON.stringify(metadata)).not.toContain('cmb-secret')
    expect(JSON.stringify(metadata)).not.toContain('do-not-send')
    expect(JSON.stringify(metadata)).not.toContain('get-/private')
  })
})
