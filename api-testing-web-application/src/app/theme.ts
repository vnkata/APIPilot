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
  const dark = mode === 'dark'
  const backgroundDefault = dark ? '#080c12' : '#f4f7fb'
  const paper = dark ? '#101720' : '#ffffff'
  const elevated = dark ? '#131c27' : '#f8fbff'
  const dividerColor = dark ? alpha('#cbd5e1', 0.14) : '#d7e0ea'
  const focusColor = dark ? '#38bdf8' : '#2563eb'
  const selectedSurface = dark ? alpha('#38bdf8', 0.16) : alpha('#2563eb', 0.09)
  const hoverSurface = dark ? alpha('#38bdf8', 0.08) : alpha('#2563eb', 0.05)
  const textPrimary = dark ? '#e5edf7' : '#102033'
  const textSecondary = dark ? '#94a3b8' : '#526173'

  return createTheme({
    palette: {
      mode,
      background: {
        default: backgroundDefault,
        paper,
      },
      primary: {
        main: '#2563eb',
        dark: '#1d4ed8',
        light: '#60a5fa',
      },
      secondary: {
        main: '#0f766e',
      },
      success: {
        main: '#059669',
      },
      warning: {
        main: '#d97706',
      },
      error: {
        main: '#dc2626',
      },
      divider: dividerColor,
      text: {
        primary: textPrimary,
        secondary: textSecondary,
      },
      status: {
        danger: '#dc2626',
        neutral: textSecondary,
        success: '#059669',
        warning: '#d97706',
      },
    },
    shape: {
      borderRadius: 6,
    },
    typography: {
      fontFamily: [
        'Roboto',
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'sans-serif',
      ].join(','),
      h1: { fontSize: '2rem', fontWeight: 800, letterSpacing: 0, lineHeight: 1.15 },
      h2: { fontSize: '1.45rem', fontWeight: 800, letterSpacing: 0, lineHeight: 1.2 },
      h3: { fontSize: '1rem', fontWeight: 750, letterSpacing: 0, lineHeight: 1.3 },
      body2: { lineHeight: 1.55 },
      button: { fontWeight: 700, letterSpacing: 0, textTransform: 'none' },
      caption: { fontSize: '0.75rem', letterSpacing: 0, lineHeight: 1.35 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            background:
              dark
                ? `linear-gradient(180deg, ${backgroundDefault} 0%, #0b1118 100%)`
                : `linear-gradient(180deg, ${backgroundDefault} 0%, #eef4fb 100%)`,
          },
        },
      },
      MuiButtonBase: {
        defaultProps: {
          disableRipple: true,
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            boxShadow: 'none',
          },
          outlined: {
            borderColor: dividerColor,
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
            borderColor: dividerColor,
            borderRadius: 6,
            boxShadow: dark ? '0 18px 50px rgba(0, 0, 0, 0.22)' : '0 16px 40px rgba(15, 23, 42, 0.05)',
          },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: {
            alignItems: 'flex-start',
            border: `1px solid ${dividerColor}`,
            borderRadius: 6,
          },
        },
      },
      MuiChip: {
        defaultProps: {
          size: 'small',
        },
        styleOverrides: {
          root: {
            borderRadius: 5,
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
            backgroundColor: paper,
            borderColor: dividerColor,
            borderRadius: 6,
            fontSize: '0.82rem',
          },
          cell: {
            borderTopColor: dividerColor,
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
            backgroundColor: elevated,
            borderBottomColor: dividerColor,
          },
          columnHeaderTitle: {
            color: textSecondary,
            fontSize: '0.76rem',
            fontWeight: 800,
            textTransform: 'uppercase',
          },
          footerContainer: {
            borderTopColor: dividerColor,
            minHeight: 44,
          },
          row: {
            '&:hover': {
              backgroundColor: hoverSurface,
            },
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            backgroundImage: 'none',
            backgroundColor: paper,
            borderColor: dividerColor,
          },
        },
      },
      MuiIconButton: {
        styleOverrides: {
          root: {
            borderRadius: 6,
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
            borderRadius: 6,
            border: '1px solid transparent',
            '&.Mui-focusVisible': {
              outline: `2px solid ${focusColor}`,
              outlineOffset: 2,
            },
            '&.Mui-selected': {
              backgroundColor: selectedSurface,
              borderColor: alpha(focusColor, 0.35),
              color: focusColor,
              '&:hover': {
                backgroundColor: alpha(focusColor, dark ? 0.18 : 0.1),
              },
            },
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            backgroundImage: 'none',
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            fontSize: '0.78rem',
            fontWeight: 800,
            minHeight: 36,
            textTransform: 'none',
          },
        },
      },
      MuiToggleButton: {
        styleOverrides: {
          root: {
            borderColor: dividerColor,
            borderRadius: 6,
            fontWeight: 800,
            textTransform: 'none',
            '&.Mui-selected': {
              backgroundColor: selectedSurface,
              color: focusColor,
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
