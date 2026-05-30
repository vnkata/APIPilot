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
  store.subscribe(() => {
    saveProductTourState(
      selectSerializableProductTourState(store.getState().productTour),
    )
    saveWorkspacePreferencesState(
      selectSerializableWorkspacePreferences(store.getState().workspacePreferences),
    )
  })
}

export type AppStore = ReturnType<typeof createAppStore>
export type RootState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
