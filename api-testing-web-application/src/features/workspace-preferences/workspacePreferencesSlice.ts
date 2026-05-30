import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import { z } from 'zod'

export type WorkspaceDensity = 'compact' | 'comfortable'
export type WorkspaceThemeMode = 'light' | 'dark'
export type GraphLayoutMode = 'dagre' | 'grid'

export type WorkspacePreferencesState = {
  density: WorkspaceDensity
  graphLayoutMode: GraphLayoutMode
  sidebarCollapsed: boolean
  tableDensity: WorkspaceDensity
  themeMode: WorkspaceThemeMode
}

export const workspacePreferencesStorageKey = 'apipilot.workspacePreferences.v1'

export const initialWorkspacePreferencesState: WorkspacePreferencesState = {
  density: 'compact',
  graphLayoutMode: 'dagre',
  sidebarCollapsed: false,
  tableDensity: 'compact',
  themeMode: 'dark',
}

const persistedPreferencesSchema = z.object({
  density: z.enum(['compact', 'comfortable']).catch(initialWorkspacePreferencesState.density),
  graphLayoutMode: z.enum(['dagre', 'grid']).catch(initialWorkspacePreferencesState.graphLayoutMode),
  sidebarCollapsed: z.boolean().catch(initialWorkspacePreferencesState.sidebarCollapsed),
  tableDensity: z.enum(['compact', 'comfortable']).catch(initialWorkspacePreferencesState.tableDensity),
  themeMode: z.enum(['light', 'dark']).catch(initialWorkspacePreferencesState.themeMode),
})

const workspacePreferencesSlice = createSlice({
  name: 'workspacePreferences',
  initialState: initialWorkspacePreferencesState,
  reducers: {
    setDensity(state, action: PayloadAction<WorkspaceDensity>) {
      state.density = action.payload
    },
    setGraphLayoutMode(state, action: PayloadAction<GraphLayoutMode>) {
      state.graphLayoutMode = action.payload
    },
    setSidebarCollapsed(state, action: PayloadAction<boolean>) {
      state.sidebarCollapsed = action.payload
    },
    setTableDensity(state, action: PayloadAction<WorkspaceDensity>) {
      state.tableDensity = action.payload
    },
    setThemeMode(state, action: PayloadAction<WorkspaceThemeMode>) {
      state.themeMode = action.payload
    },
  },
})

export const {
  setDensity,
  setGraphLayoutMode,
  setSidebarCollapsed,
  setTableDensity,
  setThemeMode,
} = workspacePreferencesSlice.actions

export const workspacePreferencesReducer = workspacePreferencesSlice.reducer

export function selectSerializableWorkspacePreferences(
  state: WorkspacePreferencesState,
): WorkspacePreferencesState {
  return {
    density: state.density,
    graphLayoutMode: state.graphLayoutMode,
    sidebarCollapsed: state.sidebarCollapsed,
    tableDensity: state.tableDensity,
    themeMode: state.themeMode,
  }
}

export function loadWorkspacePreferencesState(): WorkspacePreferencesState {
  if (typeof window === 'undefined') return initialWorkspacePreferencesState

  try {
    const rawValue = window.localStorage.getItem(workspacePreferencesStorageKey)
    if (!rawValue) return initialWorkspacePreferencesState
    return persistedPreferencesSchema.parse(JSON.parse(rawValue))
  } catch {
    return initialWorkspacePreferencesState
  }
}

export function saveWorkspacePreferencesState(state: WorkspacePreferencesState) {
  if (typeof window === 'undefined') return

  window.localStorage.setItem(
    workspacePreferencesStorageKey,
    JSON.stringify(selectSerializableWorkspacePreferences(state)),
  )
}

export const selectWorkspacePreferences = (state: {
  workspacePreferences: WorkspacePreferencesState
}) => state.workspacePreferences

export const selectThemeMode = (state: { workspacePreferences: WorkspacePreferencesState }) =>
  state.workspacePreferences.themeMode
