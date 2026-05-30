import { alpha } from '@mui/material/styles'

import type { WorkspaceThemeMode } from '../features/workspace-preferences/workspacePreferencesSlice'

export type AppTone = 'danger' | 'info' | 'neutral' | 'success' | 'warning'

export type AppToneToken = {
  border: string
  bg: string
  fg: string
}

export type HttpMethodToken =
  | 'DELETE'
  | 'GET'
  | 'HEAD'
  | 'OPTIONS'
  | 'PATCH'
  | 'POST'
  | 'PUT'
  | 'UNKNOWN'

export type StatusCodeToken =
  | 'clientError'
  | 'redirect'
  | 'serverError'
  | 'success'
  | 'unknown'

export type TestResultToken = 'failed' | 'passed' | 'pending' | 'skipped' | 'unknown'

export type AppThemeTokens = {
  border: {
    default: string
    strong: string
    subtle: string
  }
  code: {
    background: string
    border: string
    gutter: string
    text: string
  }
  focus: {
    outline: string
    ring: string
    shadow: string
  }
  gradient: {
    app: string
    panel: string
    topBar: string
  }
  httpMethod: Record<HttpMethodToken, AppToneToken>
  motion: {
    duration: {
      base: string
      fast: string
      slow: string
    }
    easing: {
      emphasized: string
      standard: string
    }
    transform: {
      hoverLift: string
      none: string
    }
    transition: {
      drawer: string
      interactive: string
      panel: string
    }
  }
  shadow: {
    elevated: string
    floating: string
    panel: string
  }
  status: Record<AppTone, AppToneToken>
  statusCode: Record<StatusCodeToken, AppToneToken>
  surface: {
    default: string
    elevated: string
    muted: string
    overlay: string
    subtle: string
  }
  testResult: Record<TestResultToken, AppToneToken>
}

function tone(fg: string, mode: WorkspaceThemeMode, bgAlpha = 0.12): AppToneToken {
  return {
    bg: alpha(fg, mode === 'dark' ? bgAlpha : 0.1),
    border: alpha(fg, mode === 'dark' ? 0.34 : 0.28),
    fg,
  }
}

export function createAppTokens(mode: WorkspaceThemeMode): AppThemeTokens {
  const dark = mode === 'dark'
  const cyan = dark ? '#38BDF8' : '#0369A1'
  const violet = dark ? '#A78BFA' : '#6D28D9'
  const emerald = dark ? '#22C55E' : '#047857'
  const amber = dark ? '#F59E0B' : '#B45309'
  const rose = dark ? '#EF4444' : '#DC2626'
  const indigo = dark ? '#818CF8' : '#4F46E5'
  const slate = dark ? '#94A3B8' : '#475569'

  const status = {
    danger: tone(rose, mode, 0.14),
    info: tone(cyan, mode, 0.13),
    neutral: tone(slate, mode, 0.12),
    success: tone(emerald, mode, 0.13),
    warning: tone(amber, mode, 0.14),
  }

  return {
    border: {
      default: dark ? alpha('#94A3B8', 0.22) : alpha('#334155', 0.18),
      strong: dark ? alpha('#94A3B8', 0.36) : alpha('#334155', 0.28),
      subtle: dark ? alpha('#94A3B8', 0.14) : alpha('#334155', 0.12),
    },
    code: {
      background: dark ? '#020617' : '#F8FAFC',
      border: dark ? alpha('#38BDF8', 0.18) : alpha('#0369A1', 0.18),
      gutter: dark ? '#1E293B' : '#E2E8F0',
      text: dark ? '#E2E8F0' : '#0F172A',
    },
    focus: {
      outline: cyan,
      ring: alpha(cyan, dark ? 0.45 : 0.3),
      shadow: `0 0 0 3px ${alpha(cyan, dark ? 0.24 : 0.18)}`,
    },
    gradient: {
      app: dark
        ? 'radial-gradient(circle at 12% -10%, rgba(56, 189, 248, 0.14), transparent 32%), linear-gradient(180deg, #070B14 0%, #0B1020 48%, #070B14 100%)'
        : 'linear-gradient(180deg, #F8FAFC 0%, #EEF4FF 100%)',
      panel: dark
        ? 'linear-gradient(180deg, rgba(23, 32, 51, 0.96), rgba(11, 16, 32, 0.98))'
        : 'linear-gradient(180deg, #FFFFFF, #F8FAFC)',
      topBar: dark
        ? 'linear-gradient(90deg, rgba(11, 16, 32, 0.96), rgba(17, 24, 39, 0.94))'
        : 'linear-gradient(90deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.94))',
    },
    httpMethod: {
      DELETE: status.danger,
      GET: status.info,
      HEAD: status.neutral,
      OPTIONS: tone(indigo, mode, 0.13),
      PATCH: tone(violet, mode, 0.13),
      POST: status.success,
      PUT: status.warning,
      UNKNOWN: status.neutral,
    },
    motion: {
      duration: {
        base: '180ms',
        fast: '120ms',
        slow: '260ms',
      },
      easing: {
        emphasized: 'cubic-bezier(0.16, 1, 0.3, 1)',
        standard: 'cubic-bezier(0.2, 0, 0, 1)',
      },
      transform: {
        hoverLift: 'translateY(-1px)',
        none: 'translateY(0)',
      },
      transition: {
        drawer: 'transform 260ms cubic-bezier(0.16, 1, 0.3, 1)',
        interactive: 'background-color 180ms cubic-bezier(0.2, 0, 0, 1), border-color 180ms cubic-bezier(0.2, 0, 0, 1), color 180ms cubic-bezier(0.2, 0, 0, 1), box-shadow 180ms cubic-bezier(0.2, 0, 0, 1), transform 180ms cubic-bezier(0.2, 0, 0, 1)',
        panel: 'border-color 180ms cubic-bezier(0.2, 0, 0, 1), box-shadow 180ms cubic-bezier(0.2, 0, 0, 1), transform 180ms cubic-bezier(0.2, 0, 0, 1)',
      },
    },
    shadow: {
      elevated: dark ? '0 24px 64px rgba(0, 0, 0, 0.32)' : '0 18px 44px rgba(15, 23, 42, 0.08)',
      floating: dark ? '0 28px 80px rgba(0, 0, 0, 0.44)' : '0 24px 60px rgba(15, 23, 42, 0.16)',
      panel: dark ? '0 16px 42px rgba(0, 0, 0, 0.22)' : '0 14px 32px rgba(15, 23, 42, 0.06)',
    },
    status,
    statusCode: {
      clientError: status.warning,
      redirect: status.info,
      serverError: status.danger,
      success: status.success,
      unknown: status.neutral,
    },
    surface: {
      default: dark ? '#111827' : '#FFFFFF',
      elevated: dark ? '#172033' : '#F8FAFC',
      muted: dark ? '#263244' : '#E2E8F0',
      overlay: dark ? alpha('#070B14', 0.84) : alpha('#FFFFFF', 0.86),
      subtle: dark ? '#1E293B' : '#F1F5F9',
    },
    testResult: {
      failed: status.danger,
      passed: status.success,
      pending: status.info,
      skipped: status.warning,
      unknown: status.neutral,
    },
  }
}
