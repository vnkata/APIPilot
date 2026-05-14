import {
  initialWorkspacePreferencesState,
  selectSerializableWorkspacePreferences,
  setSidebarCollapsed,
  setThemeMode,
  workspacePreferencesReducer,
} from './workspacePreferencesSlice'

describe('workspacePreferencesSlice', () => {
  it('stores only local UI preferences', () => {
    const state = workspacePreferencesReducer(
      initialWorkspacePreferencesState,
      setThemeMode('dark'),
    )

    expect(state.themeMode).toBe('dark')
    expect(selectSerializableWorkspacePreferences(state)).toEqual({
      density: 'compact',
      graphLayoutMode: 'dagre',
      sidebarCollapsed: false,
      tableDensity: 'compact',
      themeMode: 'dark',
    })
  })

  it('updates sidebar density preferences without server payload fields', () => {
    const state = workspacePreferencesReducer(
      initialWorkspacePreferencesState,
      setSidebarCollapsed(true),
    )

    expect(state.sidebarCollapsed).toBe(true)
    expect(JSON.stringify(state)).not.toContain('run_name')
    expect(JSON.stringify(state)).not.toContain('headers')
    expect(JSON.stringify(state)).not.toContain('response_body')
  })
})
