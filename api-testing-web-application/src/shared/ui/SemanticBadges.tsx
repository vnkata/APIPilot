import { Chip, type ChipProps } from '@mui/material'
import { useTheme } from '@mui/material/styles'

import type { AppToneToken, HttpMethodToken, StatusCodeToken, TestResultToken } from '../../theme/tokens'
import { getStatusCodeToken } from './semanticBadgeUtils'

type BadgeSize = Extract<ChipProps['size'], 'medium' | 'small'>

type ThemedBadgeProps = {
  label: string
  size?: BadgeSize
  token: AppToneToken
  variant?: 'filled' | 'outlined'
}

const methodLabels = new Set<HttpMethodToken>([
  'DELETE',
  'GET',
  'HEAD',
  'OPTIONS',
  'PATCH',
  'POST',
  'PUT',
])

const statusCodeLabels: Record<StatusCodeToken, string> = {
  clientError: 'Client error',
  redirect: 'Redirect',
  serverError: 'Server error',
  success: 'Success',
  unknown: 'Unknown status',
}

const testResultLabels: Record<TestResultToken, string> = {
  failed: 'Failed',
  passed: 'Passed',
  pending: 'Pending',
  skipped: 'Skipped',
  unknown: 'Unknown',
}

function ThemedBadge({ label, size = 'small', token, variant = 'filled' }: ThemedBadgeProps) {
  return (
    <Chip
      label={label}
      size={size}
      sx={{
        bgcolor: variant === 'filled' ? token.bg : 'transparent',
        borderColor: token.border,
        color: token.fg,
        fontVariantNumeric: 'tabular-nums',
      }}
      variant="outlined"
    />
  )
}

function normalizeMethod(method: string | null | undefined): HttpMethodToken {
  const value = method?.toUpperCase() as HttpMethodToken | undefined
  return value && methodLabels.has(value) ? value : 'UNKNOWN'
}

function normalizeTestResult(result: string | null | undefined): TestResultToken {
  const value = result?.toLowerCase()
  if (value === 'passed' || value === 'pass') return 'passed'
  if (value === 'failed' || value === 'fail') return 'failed'
  if (value === 'skipped' || value === 'skip') return 'skipped'
  if (value === 'pending') return 'pending'
  return 'unknown'
}

export function HttpMethodBadge({
  method,
  size,
}: {
  method: string | null | undefined
  size?: BadgeSize
}) {
  const theme = useTheme()
  const normalized = normalizeMethod(method)
  return <ThemedBadge label={normalized} size={size} token={theme.apiTesting.httpMethod[normalized]} />
}

export function StatusCodeBadge({
  statusCode,
  size,
}: {
  statusCode: number | string | null | undefined
  size?: BadgeSize
}) {
  const theme = useTheme()
  const group = getStatusCodeToken(statusCode)
  const codeLabel = statusCode ?? 'Unknown'
  return (
    <ThemedBadge
      label={`${codeLabel} ${statusCodeLabels[group]}`}
      size={size}
      token={theme.apiTesting.statusCode[group]}
    />
  )
}

export function TestResultBadge({
  count,
  result,
  size,
}: {
  count?: number
  result: string | null | undefined
  size?: BadgeSize
}) {
  const theme = useTheme()
  const normalized = normalizeTestResult(result)
  const label = count === undefined ? testResultLabels[normalized] : `${count} ${testResultLabels[normalized]}`
  return <ThemedBadge label={label} size={size} token={theme.apiTesting.testResult[normalized]} />
}
