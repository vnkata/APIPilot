import { configureStore } from '@reduxjs/toolkit'

import {
  initialWorkspacePreferencesState,
  loadWorkspacePreferencesState,
  saveWorkspacePreferencesState,
  selectSerializableWorkspacePreferences,
  workspacePreferencesReducer,
  type WorkspacePreferencesState,
} from '../features/workspace-preferences/workspacePreferencesSlice'

export type AppPreloadedState = {
  workspacePreferences?: WorkspacePreferencesState
}

export function createAppStore(preloadedState: AppPreloadedState = {}) {
  return configureStore({
    reducer: {
      workspacePreferences: workspacePreferencesReducer,
    },
    preloadedState: {
      workspacePreferences:
        preloadedState.workspacePreferences ?? initialWorkspacePreferencesState,
    },
    devTools: import.meta.env.DEV,
  })
}

export const store = createAppStore({
  workspacePreferences: loadWorkspacePreferencesState(),
})

if (typeof window !== 'undefined') {
  store.subscribe(() => {
    saveWorkspacePreferencesState(
      selectSerializableWorkspacePreferences(store.getState().workspacePreferences),
    )
  })
}

export type AppStore = ReturnType<typeof createAppStore>
export type RootState = ReturnType<AppStore['getState']>
export type AppDispatch = AppStore['dispatch']
