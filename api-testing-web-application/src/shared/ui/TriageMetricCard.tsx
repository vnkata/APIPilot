import { alpha, useTheme } from '@mui/material/styles'
import { Card, CardContent, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

type TriageTone = 'danger' | 'neutral' | 'success' | 'warning'

type TriageMetricCardProps = {
  caption?: ReactNode
  label: string
  tone?: TriageTone
  value: ReactNode
}

function toneColor(tone: TriageTone, mode: 'dark' | 'light') {
  if (tone === 'danger') return mode === 'dark' ? '#fb7185' : '#dc2626'
  if (tone === 'warning') return mode === 'dark' ? '#fbbf24' : '#b45309'
  if (tone === 'success') return mode === 'dark' ? '#34d399' : '#047857'
  return mode === 'dark' ? '#93c5fd' : '#2563eb'
}

export function TriageMetricCard({
  caption,
  label,
  tone = 'neutral',
  value,
}: TriageMetricCardProps) {
  const theme = useTheme()
  const accent = toneColor(tone, theme.palette.mode)

  return (
    <Card
      variant="outlined"
      sx={{
        height: '100%',
        overflow: 'hidden',
        position: 'relative',
        '&::before': {
          bgcolor: accent,
          content: '""',
          height: '100%',
          left: 0,
          position: 'absolute',
          top: 0,
          width: 3,
        },
      }}
    >
      <CardContent>
        <Stack spacing={0.75}>
          <Typography color="text.secondary" sx={{ fontWeight: 700, textTransform: 'uppercase' }} variant="caption">
            {label}
          </Typography>
          <Typography component="div" sx={{ color: accent }} variant="h2">
            {value}
          </Typography>
          {caption ? (
            <Typography
              sx={{
                bgcolor: alpha(accent, theme.palette.mode === 'dark' ? 0.12 : 0.08),
                borderRadius: 1,
                color: 'text.secondary',
                px: 1,
                py: 0.5,
              }}
              variant="body2"
            >
              {caption}
            </Typography>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  )
}
