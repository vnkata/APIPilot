import { describe, expect, it, vi } from 'vitest'

import {
  activationOnboardingReducer,
  activationOnboardingStorageKey,
  completeActivationStep,
  dismissActivation,
  initialActivationOnboardingState,
  loadActivationOnboardingState,
  saveActivationOnboardingState,
  selectSerializableActivationOnboardingState,
  skipActivationStep,
  startActivation,
} from './activationOnboardingSlice'

describe('activationOnboardingSlice', () => {
  it('tracks Combination HITL activation progress per run', () => {
    let state = activationOnboardingReducer(
      initialActivationOnboardingState,
      startActivation({ runName: 'Run A' }),
    )

    state = activationOnboardingReducer(
      state,
      completeActivationStep({ runName: 'Run A', stepId: 'open_combination_table' }),
    )
    state = activationOnboardingReducer(
      state,
      completeActivationStep({ runName: 'Run B', stepId: 'open_review_workspace' }),
    )
    state = activationOnboardingReducer(
      state,
      skipActivationStep({ runName: 'Run A', stepId: 'run_evidence' }),
    )

    expect(state.progressByRunName['Run A']?.active).toBe(true)
    expect(state.progressByRunName['Run A']?.completedStepIds.open_combination_table).toBe(true)
    expect(state.progressByRunName['Run A']?.skippedStepIds.run_evidence).toBe(true)
    expect(state.progressByRunName['Run A']?.completedStepIds.open_review_workspace).toBeUndefined()
    expect(state.progressByRunName['Run B']?.completedStepIds.open_review_workspace).toBe(true)
  })

  it('dismisses and resumes a checklist without losing completed steps', () => {
    let state = activationOnboardingReducer(
      initialActivationOnboardingState,
      completeActivationStep({ runName: 'Run A', stepId: 'select_eligible_row' }),
    )
    state = activationOnboardingReducer(state, dismissActivation({ runName: 'Run A' }))

    expect(state.progressByRunName['Run A']?.active).toBe(false)
    expect(state.progressByRunName['Run A']?.dismissed).toBe(true)
    expect(state.progressByRunName['Run A']?.completedStepIds.select_eligible_row).toBe(true)

    state = activationOnboardingReducer(state, startActivation({ runName: 'Run A' }))

    expect(state.progressByRunName['Run A']?.active).toBe(true)
    expect(state.progressByRunName['Run A']?.dismissed).toBe(false)
    expect(state.progressByRunName['Run A']?.completedStepIds.select_eligible_row).toBe(true)
  })

  it('persists only durable activation fields', () => {
    const state = activationOnboardingReducer(
      initialActivationOnboardingState,
      completeActivationStep({ runName: 'Run A', stepId: 'finalize_decision' }),
    )
    const serializable = selectSerializableActivationOnboardingState(state)

    expect(serializable.progressByRunName['Run A']?.completedStepIds.finalize_decision).toBe(true)
    expect('promptRunName' in serializable).toBe(false)
  })

  it('loads valid localStorage state and recovers from invalid data', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem')
    saveActivationOnboardingState({
      progressByRunName: {
        'Run A': {
          active: false,
          completedStepIds: { finalize_decision: true },
          dismissed: false,
          skippedStepIds: {},
        },
      },
    })

    expect(setItem).toHaveBeenCalledWith(activationOnboardingStorageKey, expect.any(String))
    expect(loadActivationOnboardingState()).toMatchObject({
      progressByRunName: {
        'Run A': {
          completedStepIds: { finalize_decision: true },
        },
      },
    })

    window.localStorage.setItem(activationOnboardingStorageKey, '{broken')
    expect(loadActivationOnboardingState()).toMatchObject({
      progressByRunName: {},
    })
    setItem.mockRestore()
  })
})
