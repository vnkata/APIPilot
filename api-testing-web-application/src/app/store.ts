import { configureStore } from '@reduxjs/toolkit'

import {
  initialProductTourPersistedState,
  loadProductTourState,
  productTourReducer,
  saveProductTourState,
  selectSerializableProductTourState,
  type ProductTourPersistedState,
} from '../features/product-tour/productTourSlice'
import {
  activationOnboardingReducer,
  initialActivationOnboardingPersistedState,
  loadActivationOnboardingState,
  saveActivationOnboardingState,
  selectSerializableActivationOnboardingState,
  type ActivationOnboardingPersistedState,
} from '../features/product-tour/activationOnboardingSlice'
import {
  initialWorkspacePreferencesState,
  loadWorkspacePreferencesState,
  saveWorkspacePreferencesState,
  selectSerializableWorkspacePreferences,
  workspacePreferencesReducer,
  type WorkspacePreferencesState,
} from '../features/workspace-preferences/workspacePreferencesSlice'

export type AppPreloadedState = {
  activationOnboarding?: ActivationOnboardingPersistedState
  productTour?: ProductTourPersistedState
  workspacePreferences?: WorkspacePreferencesState
}

export function createAppStore(preloadedState: AppPreloadedState = {}) {
  return configureStore({
    reducer: {
      activationOnboarding: activationOnboardingReducer,
      productTour: productTourReducer,
      workspacePreferences: workspacePreferencesReducer,
    },
    preloadedState: {
      activationOnboarding:
        preloadedState.activationOnboarding ?? initialActivationOnboardingPersistedState,
      productTour: {
        ...initialProductTourPersistedState,
        ...(preloadedState.productTour ?? initialProductTourPersistedState),
        activeStepIndex: 0,
      },
      workspacePreferences:
        preloadedState.workspacePreferences ?? initialWorkspacePreferencesState,
    },
    devTools: import.meta.env.DEV,
  })
}

export const store = createAppStore({
  activationOnboarding: loadActivationOnboardingState(),
  productTour: loadProductTourState(),
  workspacePreferences: loadWorkspacePreferencesState(),
})

if (typeof window !== 'undefined') {
  let previousActivationOnboardingState = JSON.stringify(
    selectSerializableActivationOnboardingState(store.getState().activationOnboarding),
  )
  let previousProductTourState = JSON.stringify(
    selectSerializableProductTourState(store.getState().productTour),
  )
  let previousWorkspacePreferencesState = JSON.stringify(
    selectSerializableWorkspacePreferences(store.getState().workspacePreferences),
  )

  store.subscribe(() => {
    const nextActivationOnboardingState = selectSerializableActivationOnboardingState(
      store.getState().activationOnboarding,
    )
    const nextProductTourState = selectSerializableProductTourState(store.getState().productTour)
    const nextWorkspacePreferencesState = selectSerializableWorkspacePreferences(
      store.getState().workspacePreferences,
    )
    const serializedActivationOnboardingState = JSON.stringify(nextActivationOnboardingState)
    const serializedProductTourState = JSON.stringify(nextProductTourState)
    const serializedWorkspacePreferencesState = JSON.stringify(nextWorkspacePreferencesState)

    if (serializedActivationOnboardingState !== previousActivationOnboardingState) {
      saveActivationOnboardingState(nextActivationOnboardingState)
      previousActivationOnboardingState = serializedActivationOnboardingState
    }

    if (serializedProductTourState !== previousProductTourState) {
      saveProductTourState(nextProductTourState)
      previousProductTourState = serializedProductTourState
    }

    if (serializedWorkspacePreferencesState !== previousWorkspacePreferencesState) {
      saveWorkspacePreferencesState(nextWorkspacePreferencesState)
      previousWorkspacePreferencesState = serializedWorkspacePreferencesState
    }
  })
}

export type AppStore = ReturnType<typeof createAppStore>
export type RootState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
