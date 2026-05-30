import { createTheme } from '@mui/material/styles'
import type {} from '@mui/x-data-grid/themeAugmentation'

import type { WorkspaceThemeMode } from '../features/workspace-preferences/workspacePreferencesSlice'
import { createComponents } from './components'
import { createPalette } from './palette'
import { createShadows } from './shadows'
import { createAppTokens, type AppThemeTokens } from './tokens'
import { typography } from './typography'

declare module '@mui/material/styles' {
  interface Theme {
    apiTesting: AppThemeTokens
  }

  interface ThemeOptions {
    apiTesting?: AppThemeTokens
  }
}

export function createAppTheme(mode: WorkspaceThemeMode) {
  const tokens = createAppTokens(mode)

  return createTheme({
    apiTesting: tokens,
    breakpoints: {
      values: {
        lg: 1200,
        md: 900,
        sm: 600,
        xl: 1536,
        xs: 0,
      },
    },
    components: createComponents(tokens),
    palette: createPalette(mode, tokens),
    shadows: createShadows(mode),
    shape: {
      borderRadius: 8,
    },
    spacing: 8,
    typography,
  })
}
