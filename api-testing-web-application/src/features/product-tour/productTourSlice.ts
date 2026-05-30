import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { z } from 'zod'

import type { TourId, TourProgress, TourRole } from './productTourTypes'

export type ProductTourPersistedState = {
  dismissedPromptByTourId: Partial<Record<TourId, number>>
  progressByTourId: Partial<Record<TourId, TourProgress>>
  role: TourRole
}

export type ProductTourState = ProductTourPersistedState & {
  activeStepIndex: number
  activeTourId?: TourId
  promptTourId?: TourId
}

export const productTourStorageKey = 'apipilot.productTour.v1'

export const initialProductTourPersistedState: ProductTourPersistedState = {
  dismissedPromptByTourId: {},
  progressByTourId: {},
  role: 'qa-qc',
}

export const initialProductTourState: ProductTourState = {
  ...initialProductTourPersistedState,
  activeStepIndex: 0,
}

const tourProgressSchema = z.object({
  completedVersion: z.number().int().positive().optional().catch(undefined),
  dismissedVersion: z.number().int().positive().optional().catch(undefined),
  lastStepIndex: z.number().int().min(0).optional().catch(undefined),
  skippedVersion: z.number().int().positive().optional().catch(undefined),
})

const persistedTourStateSchema = z.object({
  dismissedPromptByTourId: z.record(z.string(), z.number().int().positive()).catch({}),
  progressByTourId: z.record(z.string(), tourProgressSchema).catch({}),
  role: z.enum(['qa-qc']).catch(initialProductTourPersistedState.role),
})

function normalizePersistedState(state: ProductTourPersistedState): ProductTourPersistedState {
  return {
    dismissedPromptByTourId: state.dismissedPromptByTourId,
    progressByTourId: state.progressByTourId,
    role: state.role,
  }
}

function mergeProgress(
  state: ProductTourState,
  tourId: TourId,
  updates: TourProgress,
) {
  state.progressByTourId[tourId] = {
    ...state.progressByTourId[tourId],
    ...updates,
  }
}

const productTourSlice = createSlice({
  name: 'productTour',
  initialState: initialProductTourState,
  reducers: {
    completeTour(state, action: PayloadAction<{ stepIndex?: number; tourId: TourId; version: number }>) {
      mergeProgress(state, action.payload.tourId, {
        completedVersion: action.payload.version,
        lastStepIndex: action.payload.stepIndex ?? state.activeStepIndex,
      })
      state.activeTourId = undefined
      state.promptTourId = undefined
      state.activeStepIndex = 0
    },
    dismissPrompt(state, action: PayloadAction<{ tourId: TourId; version: number }>) {
      state.dismissedPromptByTourId[action.payload.tourId] = action.payload.version
      if (state.promptTourId === action.payload.tourId) {
        state.promptTourId = undefined
      }
    },
    nextStep(state, action: PayloadAction<{ maxStepIndex: number }>) {
      state.activeStepIndex = Math.min(state.activeStepIndex + 1, action.payload.maxStepIndex)
    },
    previousStep(state) {
      state.activeStepIndex = Math.max(state.activeStepIndex - 1, 0)
    },
    resetTourProgress(state, action: PayloadAction<{ tourId?: TourId } | undefined>) {
      const tourId = action.payload?.tourId
      if (tourId) {
        delete state.dismissedPromptByTourId[tourId]
        delete state.progressByTourId[tourId]
        if (state.activeTourId === tourId) state.activeTourId = undefined
        if (state.promptTourId === tourId) state.promptTourId = undefined
        state.activeStepIndex = 0
        return
      }

      state.dismissedPromptByTourId = {}
      state.progressByTourId = {}
      state.activeTourId = undefined
      state.promptTourId = undefined
      state.activeStepIndex = 0
    },
    setPromptTour(state, action: PayloadAction<{ tourId?: TourId }>) {
      state.promptTourId = action.payload.tourId
    },
    setTourStep(state, action: PayloadAction<{ stepIndex: number }>) {
      state.activeStepIndex = Math.max(0, action.payload.stepIndex)
    },
    skipTour(state, action: PayloadAction<{ stepIndex?: number; tourId: TourId; version: number }>) {
      mergeProgress(state, action.payload.tourId, {
        lastStepIndex: action.payload.stepIndex ?? state.activeStepIndex,
        skippedVersion: action.payload.version,
      })
      state.activeTourId = undefined
      state.promptTourId = undefined
      state.activeStepIndex = 0
    },
    startTour(state, action: PayloadAction<{ stepIndex?: number; tourId: TourId }>) {
      state.activeTourId = action.payload.tourId
      state.activeStepIndex = action.payload.stepIndex ?? 0
      state.promptTourId = undefined
    },
  },
})

export const {
  completeTour,
  dismissPrompt,
  nextStep,
  previousStep,
  resetTourProgress,
  setPromptTour,
  setTourStep,
  skipTour,
  startTour,
} = productTourSlice.actions

export const productTourReducer = productTourSlice.reducer

export function selectSerializableProductTourState(
  state: ProductTourState,
): ProductTourPersistedState {
  return normalizePersistedState(state)
}

export function loadProductTourState(): ProductTourPersistedState {
  if (typeof window === 'undefined') return initialProductTourPersistedState

  try {
    const rawValue = window.localStorage.getItem(productTourStorageKey)
    if (!rawValue) return initialProductTourPersistedState
    return normalizePersistedState(persistedTourStateSchema.parse(JSON.parse(rawValue)))
  } catch {
    return initialProductTourPersistedState
  }
}

export function saveProductTourState(state: ProductTourPersistedState) {
  if (typeof window === 'undefined') return

  window.localStorage.setItem(productTourStorageKey, JSON.stringify(normalizePersistedState(state)))
}

export const selectProductTour = (state: { productTour: ProductTourState }) => state.productTour

export const selectProductTourRole = (state: { productTour: ProductTourState }) =>
  state.productTour.role
