import type { Components, Theme } from '@mui/material/styles'

import { monoFontFamily } from './typography'
import type { AppThemeTokens } from './tokens'

export function createComponents(tokens: AppThemeTokens): Components<Omit<Theme, 'components'>> {
  return {
    MuiAlert: {
      styleOverrides: {
        root: {
          alignItems: 'flex-start',
          border: `1px solid ${tokens.border.default}`,
          borderRadius: 10,
        },
      },
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: 'none',
          minHeight: 34,
          transition: tokens.motion.transition.interactive,
          '&:hover': {
            transform: tokens.motion.transform.hoverLift,
          },
          '@media (prefers-reduced-motion: reduce)': {
            transition: 'none',
            '&:hover': {
              transform: tokens.motion.transform.none,
            },
          },
        },
        outlined: {
          borderColor: tokens.border.default,
        },
      },
    },
    MuiButtonBase: {
      defaultProps: {
        disableRipple: true,
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: tokens.gradient.panel,
          borderColor: tokens.border.default,
          borderRadius: 12,
          boxShadow: tokens.shadow.panel,
          transition: tokens.motion.transition.panel,
          '@media (prefers-reduced-motion: reduce)': {
            transition: 'none',
          },
        },
      },
    },
    MuiChip: {
      defaultProps: {
        size: 'small',
      },
      styleOverrides: {
        root: {
          borderRadius: 999,
          fontWeight: 750,
          maxWidth: '100%',
        },
        label: {
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        '*': {
          boxSizing: 'border-box',
        },
        '*::selection': {
          backgroundColor: tokens.httpMethod.GET.bg,
        },
        '#root': {
          minHeight: '100vh',
        },
        body: {
          background: tokens.gradient.app,
          minWidth: 320,
          textRendering: 'optimizeLegibility',
        },
        code: {
          backgroundColor: tokens.code.background,
          border: `1px solid ${tokens.code.border}`,
          borderRadius: 6,
          color: tokens.code.text,
          fontFamily: monoFontFamily,
          fontSize: '0.8125rem',
          padding: '2px 6px',
        },
        pre: {
          fontFamily: monoFontFamily,
        },
      },
    },
    MuiDataGrid: {
      defaultProps: {
        disableColumnMenu: false,
        rowSelection: false,
      },
      styleOverrides: {
        cell: {
          borderTopColor: tokens.border.subtle,
          '&:focus, &:focus-within': {
            outline: `2px solid ${tokens.focus.ring}`,
            outlineOffset: -2,
          },
        },
        columnHeader: {
          '&:focus, &:focus-within': {
            outline: `2px solid ${tokens.focus.ring}`,
            outlineOffset: -2,
          },
        },
        columnHeaderTitle: {
          fontSize: '0.75rem',
          fontWeight: 800,
          textTransform: 'uppercase',
        },
        columnHeaders: {
          backgroundColor: tokens.surface.elevated,
          borderBottomColor: tokens.border.default,
        },
        footerContainer: {
          borderTopColor: tokens.border.default,
          minHeight: 44,
        },
        root: {
          backgroundColor: tokens.surface.default,
          borderColor: tokens.border.default,
          borderRadius: 10,
          fontSize: '0.8125rem',
        },
        row: {
          '&:hover': {
            backgroundColor: tokens.surface.elevated,
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundImage: tokens.gradient.panel,
          border: `1px solid ${tokens.border.default}`,
          borderRadius: 14,
          boxShadow: tokens.shadow.floating,
          transition: tokens.motion.transition.drawer,
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: tokens.border.subtle,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: tokens.surface.default,
          backgroundImage: tokens.gradient.panel,
          borderColor: tokens.border.default,
          transition: tokens.motion.transition.drawer,
          '@media (prefers-reduced-motion: reduce)': {
            transition: 'none',
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          minHeight: 34,
          minWidth: 34,
          transition: tokens.motion.transition.interactive,
          '&.Mui-focusVisible': {
            outline: `2px solid ${tokens.focus.outline}`,
            outlineOffset: 2,
          },
          '&:hover': {
            transform: tokens.motion.transform.hoverLift,
          },
          '@media (prefers-reduced-motion: reduce)': {
            transition: 'none',
            '&:hover': {
              transform: tokens.motion.transform.none,
            },
          },
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: {
          fontSize: '0.8125rem',
          fontWeight: 650,
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          border: '1px solid transparent',
          borderRadius: 8,
          minHeight: 38,
          transition: tokens.motion.transition.interactive,
          '&.Mui-focusVisible': {
            outline: `2px solid ${tokens.focus.outline}`,
            outlineOffset: 2,
          },
          '&.Mui-selected': {
            backgroundColor: tokens.httpMethod.GET.bg,
            borderColor: tokens.httpMethod.GET.border,
            color: tokens.httpMethod.GET.fg,
            '&:hover': {
              backgroundColor: tokens.httpMethod.GET.bg,
            },
          },
        },
      },
    },
    MuiMenu: {
      styleOverrides: {
        paper: {
          backgroundImage: tokens.gradient.panel,
          border: `1px solid ${tokens.border.default}`,
          boxShadow: tokens.shadow.floating,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontSize: '0.8125rem',
          transition: tokens.motion.transition.interactive,
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: tokens.border.default,
          },
          '&:hover .MuiOutlinedInput-notchedOutline': {
            borderColor: tokens.border.strong,
          },
          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
            borderColor: tokens.focus.outline,
            boxShadow: tokens.focus.shadow,
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
    MuiSelect: {
      styleOverrides: {
        select: {
          fontSize: '0.8125rem',
        },
      },
    },
    MuiSnackbar: {
      styleOverrides: {
        root: {
          '& .MuiPaper-root': {
            border: `1px solid ${tokens.border.default}`,
          },
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontSize: '0.8125rem',
          fontWeight: 800,
          minHeight: 38,
          textTransform: 'none',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          backgroundColor: tokens.surface.elevated,
          fontSize: '0.75rem',
          fontWeight: 800,
          textTransform: 'uppercase',
        },
        root: {
          borderBottomColor: tokens.border.subtle,
          fontSize: '0.8125rem',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: {
          borderColor: tokens.border.default,
          borderRadius: 8,
          fontSize: '0.8125rem',
          fontWeight: 800,
          minHeight: 34,
          textTransform: 'none',
          transition: tokens.motion.transition.interactive,
          '&.Mui-selected': {
            backgroundColor: tokens.httpMethod.GET.bg,
            borderColor: tokens.httpMethod.GET.border,
            color: tokens.httpMethod.GET.fg,
          },
        },
      },
    },
    MuiTooltip: {
      defaultProps: {
        arrow: true,
      },
      styleOverrides: {
        tooltip: {
          fontSize: '0.75rem',
          fontWeight: 650,
        },
      },
    },
  }
}
