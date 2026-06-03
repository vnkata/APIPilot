import { Box, Chip, Stack, Tooltip, Typography } from '@mui/material'
import { useTheme } from '@mui/material/styles'

import type { CombinationReviewResponse } from '../../../shared/api/generated/model'
import type { AppTone, AppToneToken } from '../../../theme/tokens'
import {
  deriveCombinationReviewSignal,
  type CombinationReviewFields,
  type CombinationTone,
} from '../constraintViewModels'

type BadgeSize = 'medium' | 'small'

function toneToken(tone: CombinationTone): AppTone {
  return tone
}

function pretty(value: string | null | undefined) {
  if (!value) return 'Not available'
  return value
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function ThemedCombinationBadge({
  label,
  size = 'small',
  token,
  tooltip,
  variant = 'filled',
}: {
  label: string
  size?: BadgeSize
  token: AppToneToken
  tooltip: string
  variant?: 'filled' | 'outlined'
}) {
  return (
    <Tooltip arrow title={tooltip}>
      <Chip
        label={label}
        size={size}
        sx={{
          bgcolor: variant === 'filled' ? token.bg : 'transparent',
          borderColor: token.border,
          color: token.fg,
          fontWeight: 800,
        }}
        variant="outlined"
      />
    </Tooltip>
  )
}

export function CombinationPriorityBadge({
  row,
  size,
}: {
  row: CombinationReviewFields
  size?: BadgeSize
}) {
  const theme = useTheme()
  const signal = deriveCombinationReviewSignal(row)
  const rawText = signal.rawValues.length ? ` Raw: ${signal.rawValues.join(', ')}.` : ''

  return (
    <ThemedCombinationBadge
      label={signal.label}
      size={size}
      token={theme.apiTesting.status[toneToken(signal.tone)]}
      tooltip={`${signal.description} Next action: ${signal.recommendedNextAction}.${rawText}`}
    />
  )
}

export function CombinationRelationBadge({
  relation,
  size,
}: {
  relation: string | null | undefined
  size?: BadgeSize
}) {
  const theme = useTheme()
  const tone: AppTone =
    relation === 'DISJOINT' ? 'danger'
      : relation === 'DYNAMIC_STRONGER' || relation === 'PARTIAL_OVERLAP' || relation === 'UNKNOWN' ? 'warning'
      : relation === 'EQUIVALENT' || relation === 'STATIC_STRONGER' ? 'success'
      : 'info'

  return (
    <ThemedCombinationBadge
      label={relation ? pretty(relation) : 'Unique'}
      size={size}
      token={theme.apiTesting.status[tone]}
      tooltip={`Relation: ${relation ?? 'null for unique static/dynamic rows'}. ${relationDescription(relation)}`}
      variant="outlined"
    />
  )
}

export function CombinationStatusBadge({
  size,
  status,
}: {
  size?: BadgeSize
  status: string | null | undefined
}) {
  const theme = useTheme()
  const tone: AppTone =
    status === 'CONFLICT' ? 'danger'
      : status === 'UNRESOLVED' ? 'warning'
      : status === 'RESOLVED' || status === 'VERIFIED' ? 'success'
      : status === 'UNIQUE_STATIC' || status === 'UNIQUE_DYNAMIC' ? 'info'
      : 'neutral'

  return (
    <ThemedCombinationBadge
      label={pretty(status)}
      size={size}
      token={theme.apiTesting.status[tone]}
      tooltip={`Status: ${status ?? 'not available'}. ${statusDescription(status)}`}
      variant="outlined"
    />
  )
}

export function RuntimeVerdictBadge({
  runtimeVerdict,
  size,
}: {
  runtimeVerdict: string | null | undefined
  size?: BadgeSize
}) {
  const theme = useTheme()
  const tone: AppTone =
    runtimeVerdict?.includes('CONTRADICTION') || runtimeVerdict?.includes('FAIL') ? 'danger'
      : runtimeVerdict ? 'info'
      : 'neutral'

  return (
    <ThemedCombinationBadge
      label={runtimeVerdict ? pretty(runtimeVerdict) : 'No runtime support'}
      size={size}
      token={theme.apiTesting.status[tone]}
      tooltip={`Runtime verdict: ${runtimeVerdict ?? 'none'}. Runtime evidence is support, not proof.`}
      variant="outlined"
    />
  )
}

export function ReviewStateBadge({
  review,
  row,
  size,
}: {
  review?: CombinationReviewResponse
  row?: CombinationReviewFields
  size?: BadgeSize
}) {
  const theme = useTheme()
  const reviewState = review?.review_state ?? row?.review_state
  const manualDecision = review?.manual_decision ?? row?.manual_decision
  const hasManualDecision = review?.has_manual_decision ?? row?.has_manual_decision
  const tone: AppTone = hasManualDecision || reviewState === 'FINAL_CONFIRMED' ? 'success'
    : reviewState === 'RUN_COMPLETED' || reviewState === 'DRAFT_READY' || reviewState === 'APPROVED' ? 'info'
      : reviewState === 'REOPENED' || reviewState === 'PENDING_REVIEW' ? 'warning'
        : 'neutral'

  return (
    <ThemedCombinationBadge
      label={hasManualDecision ? `Human: ${pretty(manualDecision)}` : pretty(reviewState ?? 'PENDING_REVIEW')}
      size={size}
      token={theme.apiTesting.status[tone]}
      tooltip={`Review state: ${reviewState ?? 'PENDING_REVIEW'}. Manual decision: ${manualDecision ?? 'none'}.`}
      variant={hasManualDecision ? 'filled' : 'outlined'}
    />
  )
}

export function RelationVisual({ relation }: { relation: string | null | undefined }) {
  const theme = useTheme()
  const isEquivalent = relation === 'EQUIVALENT'
  const isStaticStronger = relation === 'STATIC_STRONGER'
  const isDynamicStronger = relation === 'DYNAMIC_STRONGER'
  const isDisjoint = relation === 'DISJOINT'

  return (
    <Box
      aria-label={`Relation visual ${relation ?? 'unique'}`}
      role="img"
      sx={{
        height: 104,
        position: 'relative',
        width: '100%',
      }}
    >
      <RelationCircle
        color={theme.apiTesting.status.info}
        label="Static"
        sx={{
          left: isDisjoint ? '17%' : isDynamicStronger ? '22%' : isEquivalent ? '30%' : '24%',
          width: isStaticStronger ? 76 : isDynamicStronger ? 54 : 66,
          zIndex: isDynamicStronger ? 2 : 1,
        }}
      />
      <RelationCircle
        color={theme.apiTesting.status.warning}
        label="Dynamic"
        sx={{
          left: isDisjoint ? '58%' : isStaticStronger ? '42%' : isEquivalent ? '32%' : '43%',
          width: isDynamicStronger ? 76 : isStaticStronger ? 54 : 66,
          zIndex: isStaticStronger ? 2 : 1,
        }}
      />
      <Typography
        color="text.secondary"
        sx={{ bottom: 0, left: 0, position: 'absolute', right: 0, textAlign: 'center' }}
        variant="caption"
      >
        {relationDescription(relation)}
      </Typography>
    </Box>
  )
}

function RelationCircle({
  color,
  label,
  sx,
}: {
  color: AppToneToken
  label: string
  sx: object
}) {
  return (
    <Box
      sx={{
        alignItems: 'center',
        aspectRatio: '1 / 1',
        bgcolor: color.bg,
        border: '2px solid',
        borderColor: color.border,
        borderRadius: '50%',
        color: color.fg,
        display: 'flex',
        fontSize: 12,
        fontWeight: 900,
        justifyContent: 'center',
        position: 'absolute',
        top: 8,
        transition: (theme) => theme.apiTesting.motion.transition,
        ...sx,
      }}
    >
      {label}
    </Box>
  )
}

export function RelationGuide() {
  const relations = ['EQUIVALENT', 'STATIC_STRONGER', 'DYNAMIC_STRONGER', 'PARTIAL_OVERLAP', 'DISJOINT', 'UNKNOWN']

  return (
    <Box
      aria-label="Relation guide"
      role="region"
      sx={(theme) => ({
        border: '1px solid',
        borderColor: theme.apiTesting.border.default,
        borderRadius: 1,
        p: 1.5,
      })}
    >
      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Relation guide
        </Typography>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
          {relations.map((relation) => (
            <CombinationRelationBadge key={relation} relation={relation} />
          ))}
        </Stack>
        <Typography color="text.secondary" variant="body2">
          Relation describes the set relationship between static and dynamic constraints. Status describes lifecycle; runtime verdict is only supporting evidence.
        </Typography>
      </Stack>
    </Box>
  )
}

function relationDescription(relation: string | null | undefined) {
  if (relation === 'EQUIVALENT') return 'Static and dynamic constraints describe the same valid cases.'
  if (relation === 'STATIC_STRONGER') return 'Static constraint is more restrictive than dynamic evidence.'
  if (relation === 'DYNAMIC_STRONGER') return 'Dynamic constraint is more restrictive and needs review before finalization.'
  if (relation === 'PARTIAL_OVERLAP') return 'Static and dynamic constraints overlap but neither fully implies the other.'
  if (relation === 'DISJOINT') return 'Static and dynamic constraints appear incompatible.'
  if (relation === 'UNKNOWN') return 'The relation cannot be determined from available context.'
  return 'Unique rows have only one available constraint side.'
}

function statusDescription(status: string | null | undefined) {
  if (status === 'RESOLVED') return 'The combiner has selected a final constraint.'
  if (status === 'UNRESOLVED') return 'A reviewer should decide before this becomes final.'
  if (status === 'CONFLICT') return 'The row represents a conflict between evidence sources.'
  if (status === 'VERIFIED') return 'Runtime evidence supports the current recommendation.'
  if (status === 'UNIQUE_STATIC' || status === 'UNIQUE_DYNAMIC') return 'Only one source produced this constraint.'
  return 'Status is not available.'
}
