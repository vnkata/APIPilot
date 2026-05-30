import { Chip, type ChipProps } from '@mui/material'
import { useTheme } from '@mui/material/styles'

import type { AppTone, AppToneToken } from '../../../theme/tokens'

type BadgeSize = Extract<ChipProps['size'], 'medium' | 'small'>

type ConstraintBadgeProps = {
  label: string
  size?: BadgeSize
  tone: AppTone
  variant?: 'filled' | 'outlined'
}

function ThemedConstraintBadge({
  label,
  size = 'small',
  tone,
  variant = 'filled',
}: ConstraintBadgeProps) {
  const theme = useTheme()
  const token: AppToneToken = theme.apiTesting.status[tone]

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

function normalize(value: string | null | undefined) {
  return value?.trim() || 'unknown'
}

function pretty(value: string | boolean | null | undefined) {
  if (typeof value === 'boolean') return value ? 'Available' : 'Missing'
  return normalize(value).replaceAll('_', ' ')
}

export function ConstraintSourceBadge({ source }: { source: string | null | undefined }) {
  const normalized = normalize(source)
  const tone: AppTone =
    normalized === 'combined' ? 'success' : normalized === 'dynamic' ? 'info' : normalized === 'static' ? 'neutral' : 'warning'

  return <ThemedConstraintBadge label={pretty(normalized)} tone={tone} />
}

export function ConstraintKindBadge({ kind }: { kind: string | null | undefined }) {
  const normalized = normalize(kind)
  const tone: AppTone =
    normalized === 'unknown' ? 'warning' : normalized.includes('relation') ? 'info' : normalized === 'enum' ? 'success' : 'neutral'

  return <ThemedConstraintBadge label={pretty(normalized)} tone={tone} variant="outlined" />
}

export function AgreementBadge({ agreement }: { agreement: string | null | undefined }) {
  const normalized = normalize(agreement)
  const tone: AppTone =
    normalized === 'both_present' ? 'success' : normalized === 'combined_only' ? 'info' : normalized === 'unknown' ? 'neutral' : 'warning'

  return <ThemedConstraintBadge label={pretty(normalized)} tone={tone} />
}

export function OracleReadinessBadge({ readiness }: { readiness: string | null | undefined }) {
  const normalized = normalize(readiness)
  const tone: AppTone =
    normalized === 'verified_runtime_oracle' || normalized === 'schema_supported'
      ? 'success'
      : normalized.includes('unsupported') || normalized.includes('missing')
        ? 'danger'
        : normalized === 'unknown'
          ? 'neutral'
          : 'warning'

  return <ThemedConstraintBadge label={pretty(normalized)} tone={tone} />
}

export function CorrelationBadge({ confidence }: { confidence: string | null | undefined }) {
  const normalized = normalize(confidence)
  const tone: AppTone =
    normalized.includes('high') || normalized.includes('matched')
      ? 'success'
      : normalized.includes('low') || normalized.includes('weak')
        ? 'warning'
        : 'neutral'

  return <ThemedConstraintBadge label={pretty(normalized)} tone={tone} variant="outlined" />
}

export function AssertionBadge({ available }: { available: boolean | null | undefined }) {
  return <ThemedConstraintBadge label={available ? 'Assertion ready' : 'No assertion'} tone={available ? 'success' : 'warning'} />
}
