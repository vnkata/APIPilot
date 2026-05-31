import { describe, expect, it, vi } from 'vitest'

import {
  completeTour,
  dismissPrompt,
  initialProductTourState,
  loadProductTourState,
  productTourReducer,
  productTourStorageKey,
  resetTourProgress,
  saveProductTourState,
  selectSerializableProductTourState,
  skipTour,
  startTour,
} from './productTourSlice'

describe('productTourSlice', () => {
  it('tracks start, completion, skip, dismissal, and reset state', () => {
    let state = productTourReducer(initialProductTourState, startTour({ tourId: 'constraints-fundamentals' }))
    expect(state.activeTourId).toBe('constraints-fundamentals')
    expect(state.activeStepIndex).toBe(0)

    state = productTourReducer(state, completeTour({ stepIndex: 2, tourId: 'constraints-fundamentals', version: 1 }))
    expect(state.activeTourId).toBeUndefined()
    expect(state.progressByTourId['constraints-fundamentals']?.completedVersion).toBe(1)
    expect(state.progressByTourId['constraints-fundamentals']?.lastStepIndex).toBe(2)

    state = productTourReducer(state, startTour({ stepIndex: 1, tourId: 'graph' }))
    state = productTourReducer(state, skipTour({ tourId: 'graph', version: 1 }))
    expect(state.progressByTourId.graph?.skippedVersion).toBe(1)
    expect(state.progressByTourId.graph?.lastStepIndex).toBe(1)

    state = productTourReducer(state, dismissPrompt({ tourId: 'reports', version: 1 }))
    expect(state.dismissedPromptByTourId.reports).toBe(1)

    state = productTourReducer(state, resetTourProgress({ tourId: 'constraints-fundamentals' }))
    expect(state.progressByTourId['constraints-fundamentals']).toBeUndefined()
    expect(state.progressByTourId.graph?.skippedVersion).toBe(1)
  })

  it('persists only durable progress fields', () => {
    const state = productTourReducer(initialProductTourState, startTour({ tourId: 'constraints-fundamentals' }))
    const serializable = selectSerializableProductTourState(state)

    expect(serializable.role).toBe('qa-qc')
    expect('activeTourId' in serializable).toBe(false)
    expect('activeStepIndex' in serializable).toBe(false)
  })

  it('loads valid localStorage state and recovers from invalid data', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem')
    saveProductTourState({
      dismissedPromptByTourId: { 'constraints-fundamentals': 1 },
      progressByTourId: { 'constraints-fundamentals': { completedVersion: 1 } },
      role: 'qa-qc',
    })

    expect(setItem).toHaveBeenCalledWith(productTourStorageKey, expect.any(String))
    expect(loadProductTourState()).toMatchObject({
      dismissedPromptByTourId: { 'constraints-fundamentals': 1 },
      progressByTourId: { 'constraints-fundamentals': { completedVersion: 1 } },
      role: 'qa-qc',
    })

    window.localStorage.setItem(productTourStorageKey, '{broken')
    expect(loadProductTourState()).toMatchObject({
      dismissedPromptByTourId: {},
      progressByTourId: {},
      role: 'qa-qc',
    })
    setItem.mockRestore()
  })
})
