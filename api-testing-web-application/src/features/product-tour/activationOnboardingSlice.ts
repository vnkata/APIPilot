import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { z } from 'zod'

import type {
  ActivationOnboardingPersistedState,
  ActivationOnboardingState,
  ActivationRunProgress,
  CombinationHitlActivationStepId,
} from './activationOnboardingTypes'

export type { ActivationOnboardingPersistedState } from './activationOnboardingTypes'

type RunStepPayload = {
  runName: string
  stepId: CombinationHitlActivationStepId
}

export const activationOnboardingStorageKey = 'apipilot.activationOnboarding.v1'

export const initialActivationOnboardingPersistedState: ActivationOnboardingPersistedState = {
  progressByRunName: {},
}

export const initialActivationOnboardingState: ActivationOnboardingState = {
  ...initialActivationOnboardingPersistedState,
}

const stepProgressSchema = z.record(z.string(), z.literal(true)).catch({})

const runProgressSchema = z.object({
  active: z.boolean().catch(false),
  completedAt: z.string().optional().catch(undefined),
  completedStepIds: stepProgressSchema,
  dismissed: z.boolean().catch(false),
  skippedStepIds: stepProgressSchema,
})

const persistedActivationStateSchema = z.object({
  progressByRunName: z.record(z.string(), runProgressSchema).catch({}),
})

function normalizeProgress(progress: ActivationRunProgress): ActivationRunProgress {
  return {
    active: progress.active,
    completedAt: progress.completedAt,
    completedStepIds: progress.completedStepIds,
    dismissed: progress.dismissed,
    skippedStepIds: progress.skippedStepIds,
  }
}

function normalizePersistedState(
  state: ActivationOnboardingPersistedState,
): ActivationOnboardingPersistedState {
  return {
    progressByRunName: Object.fromEntries(
      Object.entries(state.progressByRunName).map(([runName, progress]) => [
        runName,
        normalizeProgress(progress),
      ]),
    ),
  }
}

function ensureRunProgress(state: ActivationOnboardingState, runName: string) {
  state.progressByRunName[runName] ??= {
    active: false,
    completedStepIds: {},
    dismissed: false,
    skippedStepIds: {},
  }
  return state.progressByRunName[runName]
}

const activationOnboardingSlice = createSlice({
  name: 'activationOnboarding',
  initialState: initialActivationOnboardingState,
  reducers: {
    completeActivationStep(state, action: PayloadAction<RunStepPayload>) {
      const progress = ensureRunProgress(state, action.payload.runName)
      progress.active = true
      progress.dismissed = false
      progress.completedStepIds[action.payload.stepId] = true
      delete progress.skippedStepIds[action.payload.stepId]
      if (action.payload.stepId === 'finalize_decision') {
        progress.completedAt ??= new Date().toISOString()
      }
    },
    dismissActivation(state, action: PayloadAction<{ runName: string }>) {
      const progress = ensureRunProgress(state, action.payload.runName)
      progress.active = false
      progress.dismissed = true
    },
    resetActivation(state, action: PayloadAction<{ runName?: string } | undefined>) {
      const runName = action.payload?.runName
      if (runName) {
        delete state.progressByRunName[runName]
        return
      }
      state.progressByRunName = {}
    },
    skipActivationStep(state, action: PayloadAction<RunStepPayload>) {
      const progress = ensureRunProgress(state, action.payload.runName)
      progress.active = true
      progress.dismissed = false
      if (!progress.completedStepIds[action.payload.stepId]) {
        progress.skippedStepIds[action.payload.stepId] = true
      }
    },
    startActivation(state, action: PayloadAction<{ runName: string }>) {
      const progress = ensureRunProgress(state, action.payload.runName)
      progress.active = true
      progress.dismissed = false
    },
  },
})

export const {
  completeActivationStep,
  dismissActivation,
  resetActivation,
  skipActivationStep,
  startActivation,
} = activationOnboardingSlice.actions

export const activationOnboardingReducer = activationOnboardingSlice.reducer

export function selectSerializableActivationOnboardingState(
  state: ActivationOnboardingState,
): ActivationOnboardingPersistedState {
  return normalizePersistedState(state)
}

export function loadActivationOnboardingState(): ActivationOnboardingPersistedState {
  if (typeof window === 'undefined') return initialActivationOnboardingPersistedState

  try {
    const rawValue = window.localStorage.getItem(activationOnboardingStorageKey)
    if (!rawValue) return initialActivationOnboardingPersistedState
    return normalizePersistedState(persistedActivationStateSchema.parse(JSON.parse(rawValue)))
  } catch {
    return initialActivationOnboardingPersistedState
  }
}

export function saveActivationOnboardingState(state: ActivationOnboardingPersistedState) {
  if (typeof window === 'undefined') return

  window.localStorage.setItem(
    activationOnboardingStorageKey,
    JSON.stringify(normalizePersistedState(state)),
  )
}

export const selectActivationOnboarding = (state: {
  activationOnboarding: ActivationOnboardingState
}) => state.activationOnboarding

export const selectCombinationHitlActivationProgress = (
  state: { activationOnboarding: ActivationOnboardingState },
  runName: string,
) => state.activationOnboarding.progressByRunName[runName]
