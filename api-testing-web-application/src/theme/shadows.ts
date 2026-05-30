import type { Shadows } from '@mui/material/styles'

import type { WorkspaceThemeMode } from '../features/workspace-preferences/workspacePreferencesSlice'

export function createShadows(mode: WorkspaceThemeMode): Shadows {
  const dark = mode === 'dark'
  const shadows = Array(25).fill('none') as Shadows

  shadows[1] = dark ? '0 8px 24px rgba(0, 0, 0, 0.18)' : '0 6px 18px rgba(15, 23, 42, 0.06)'
  shadows[2] = dark ? '0 14px 34px rgba(0, 0, 0, 0.24)' : '0 10px 26px rgba(15, 23, 42, 0.08)'
  shadows[3] = dark ? '0 18px 48px rgba(0, 0, 0, 0.3)' : '0 16px 36px rgba(15, 23, 42, 0.1)'
  shadows[4] = dark ? '0 24px 64px rgba(0, 0, 0, 0.36)' : '0 20px 48px rgba(15, 23, 42, 0.12)'
  shadows[5] = dark ? '0 30px 84px rgba(0, 0, 0, 0.44)' : '0 28px 64px rgba(15, 23, 42, 0.16)'

  return shadows
}
