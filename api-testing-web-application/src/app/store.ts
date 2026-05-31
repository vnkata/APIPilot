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
  initialWorkspacePreferencesState,
  loadWorkspacePreferencesState,
  saveWorkspacePreferencesState,
  selectSerializableWorkspacePreferences,
  workspacePreferencesReducer,
  type WorkspacePreferencesState,
} from '../features/workspace-preferences/workspacePreferencesSlice'

export type AppPreloadedState = {
  productTour?: ProductTourPersistedState
  workspacePreferences?: WorkspacePreferencesState
}

export function createAppStore(preloadedState: AppPreloadedState = {}) {
  return configureStore({
    reducer: {
      productTour: productTourReducer,
      workspacePreferences: workspacePreferencesReducer,
    },
    preloadedState: {
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
  productTour: loadProductTourState(),
  workspacePreferences: loadWorkspacePreferencesState(),
})

if (typeof window !== 'undefined') {
  let previousProductTourState = JSON.stringify(
    selectSerializableProductTourState(store.getState().productTour),
  )
  let previousWorkspacePreferencesState = JSON.stringify(
    selectSerializableWorkspacePreferences(store.getState().workspacePreferences),
  )

  store.subscribe(() => {
    const nextProductTourState = selectSerializableProductTourState(store.getState().productTour)
    const nextWorkspacePreferencesState = selectSerializableWorkspacePreferences(
      store.getState().workspacePreferences,
    )
    const serializedProductTourState = JSON.stringify(nextProductTourState)
    const serializedWorkspacePreferencesState = JSON.stringify(nextWorkspacePreferencesState)

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
