import { Button, Card, CardContent, Chip, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

type EvidenceSummaryCardProps = {
  actionLabel?: string
  badges?: ReactNode
  description?: ReactNode
  metric?: ReactNode
  onAction?: () => void
  title: ReactNode
  tone?: 'danger' | 'neutral' | 'success' | 'warning'
}

function borderColor(tone: EvidenceSummaryCardProps['tone']) {
  if (tone === 'danger') return 'error.main'
  if (tone === 'warning') return 'warning.main'
  if (tone === 'success') return 'success.main'
  return 'divider'
}

export function EvidenceSummaryCard({
  actionLabel = 'Inspect',
  badges,
  description,
  metric,
  onAction,
  title,
  tone = 'neutral',
}: EvidenceSummaryCardProps) {
  return (
    <Card
      variant="outlined"
      sx={{
        borderColor: borderColor(tone),
        height: '100%',
      }}
    >
      <CardContent>
        <Stack spacing={1.25}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <Stack spacing={0.5} sx={{ minWidth: 0 }}>
              <Typography component="h3" sx={{ overflowWrap: 'anywhere' }} variant="h3">
                {title}
              </Typography>
              {description ? (
                <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="body2">
                  {description}
                </Typography>
              ) : null}
            </Stack>
            {metric ? <Chip color={tone === 'danger' ? 'error' : 'default'} label={metric} size="small" /> : null}
          </Stack>
          {badges ? <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>{badges}</Stack> : null}
          {onAction ? (
            <Button onClick={onAction} size="small" variant="outlined">
              {actionLabel}
            </Button>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  )
}
