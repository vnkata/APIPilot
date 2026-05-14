import { alpha, createTheme } from '@mui/material/styles'
import type {} from '@mui/x-data-grid/themeAugmentation'

import type { WorkspaceThemeMode } from '../features/workspace-preferences/workspacePreferencesSlice'

declare module '@mui/material/styles' {
  interface Palette {
    status: {
      danger: string
      neutral: string
      success: string
      warning: string
    }
  }

  interface PaletteOptions {
    status?: {
      danger: string
      neutral: string
      success: string
      warning: string
    }
  }
}

export function createAppTheme(mode: WorkspaceThemeMode) {
  const dividerColor = mode === 'dark' ? alpha('#d0d7de', 0.16) : '#d8dee4'
  const focusColor = mode === 'dark' ? '#79c0ff' : '#0969da'
  const selectedSurface = mode === 'dark' ? alpha('#1f6feb', 0.2) : alpha('#1f6feb', 0.08)

  return createTheme({
    palette: {
      mode,
      background: {
        default: mode === 'dark' ? '#0f1419' : '#f7f9fc',
        paper: mode === 'dark' ? '#151c24' : '#ffffff',
      },
      primary: {
        main: '#1f6feb',
      },
      secondary: {
        main: '#7c3aed',
      },
      success: {
        main: '#238636',
      },
      warning: {
        main: '#b7791f',
      },
      error: {
        main: '#cf222e',
      },
      status: {
        danger: '#cf222e',
        neutral: '#57606a',
        success: '#238636',
        warning: '#b7791f',
      },
    },
    shape: {
      borderRadius: 8,
    },
    typography: {
      fontFamily: [
        'Roboto',
        'Inter',
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'sans-serif',
      ].join(','),
      h1: { fontSize: '2rem', fontWeight: 700, lineHeight: 1.2 },
      h2: { fontSize: '1.5rem', fontWeight: 700, lineHeight: 1.25 },
      h3: { fontSize: '1.25rem', fontWeight: 700, lineHeight: 1.3 },
      button: { fontWeight: 600, textTransform: 'none' },
    },
    components: {
      MuiButtonBase: {
        defaultProps: {
          disableRipple: true,
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            borderRadius: 8,
          },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: {
            alignItems: 'flex-start',
            border: `1px solid ${dividerColor}`,
            borderRadius: 8,
          },
        },
      },
      MuiChip: {
        defaultProps: {
          size: 'small',
        },
        styleOverrides: {
          root: {
            borderRadius: 6,
            fontWeight: 600,
            maxWidth: '100%',
          },
          label: {
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          },
        },
      },
      MuiDataGrid: {
        defaultProps: {
          disableColumnMenu: false,
          rowSelection: false,
        },
        styleOverrides: {
          root: {
            borderColor: dividerColor,
            borderRadius: 8,
            fontSize: '0.875rem',
          },
          cell: {
            '&:focus, &:focus-within': {
              outline: `2px solid ${alpha(focusColor, 0.55)}`,
              outlineOffset: -2,
            },
          },
          columnHeader: {
            '&:focus, &:focus-within': {
              outline: `2px solid ${alpha(focusColor, 0.55)}`,
              outlineOffset: -2,
            },
          },
          columnHeaders: {
            backgroundColor: mode === 'dark' ? '#111820' : '#f6f8fa',
            borderBottomColor: dividerColor,
          },
          footerContainer: {
            borderTopColor: dividerColor,
            minHeight: 44,
          },
          row: {
            '&:hover': {
              backgroundColor: mode === 'dark' ? alpha('#79c0ff', 0.08) : alpha('#0969da', 0.04),
            },
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            borderColor: dividerColor,
          },
        },
      },
      MuiIconButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            '&.Mui-focusVisible': {
              outline: `2px solid ${focusColor}`,
              outlineOffset: 2,
            },
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            '&.Mui-focusVisible': {
              outline: `2px solid ${focusColor}`,
              outlineOffset: 2,
            },
            '&.Mui-selected': {
              backgroundColor: selectedSurface,
              '&:hover': {
                backgroundColor: alpha(focusColor, mode === 'dark' ? 0.26 : 0.12),
              },
            },
          },
        },
      },
      MuiTooltip: {
        defaultProps: {
          arrow: true,
        },
      },
    },
  })
}
