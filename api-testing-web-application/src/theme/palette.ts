import type { PaletteOptions } from '@mui/material/styles'

import type { WorkspaceThemeMode } from '../features/workspace-preferences/workspacePreferencesSlice'
import type { AppThemeTokens } from './tokens'

export function createPalette(mode: WorkspaceThemeMode, tokens: AppThemeTokens): PaletteOptions {
  const dark = mode === 'dark'

  return {
    mode,
    background: {
      default: dark ? '#070B14' : '#F8FAFC',
      paper: dark ? '#0B1020' : '#FFFFFF',
    },
    divider: tokens.border.default,
    error: {
      contrastText: '#FFFFFF',
      dark: dark ? '#BE123C' : '#B91C1C',
      light: dark ? '#FB7185' : '#FCA5A5',
      main: dark ? '#EF4444' : '#DC2626',
    },
    info: {
      contrastText: dark ? '#020617' : '#FFFFFF',
      dark: dark ? '#0284C7' : '#075985',
      light: dark ? '#7DD3FC' : '#38BDF8',
      main: dark ? '#38BDF8' : '#0369A1',
    },
    primary: {
      contrastText: '#020617',
      dark: '#0284C7',
      light: '#7DD3FC',
      main: '#38BDF8',
    },
    secondary: {
      contrastText: '#FFFFFF',
      dark: '#7C3AED',
      light: '#C4B5FD',
      main: '#A78BFA',
    },
    success: {
      contrastText: dark ? '#020617' : '#FFFFFF',
      dark: dark ? '#15803D' : '#065F46',
      light: dark ? '#86EFAC' : '#34D399',
      main: dark ? '#22C55E' : '#047857',
    },
    text: {
      disabled: dark ? '#64748B' : '#94A3B8',
      primary: dark ? '#F8FAFC' : '#0F172A',
      secondary: dark ? '#CBD5E1' : '#475569',
    },
    warning: {
      contrastText: '#020617',
      dark: dark ? '#D97706' : '#92400E',
      light: dark ? '#FBBF24' : '#FCD34D',
      main: dark ? '#F59E0B' : '#B45309',
    },
  }
}
