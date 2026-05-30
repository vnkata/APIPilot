import { alpha, useTheme } from '@mui/material/styles'
import { Card, CardContent, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'
import type { AppTone } from '../../theme/tokens'

type TriageTone = 'danger' | 'neutral' | 'success' | 'warning'

type TriageMetricCardProps = {
  caption?: ReactNode
  label: string
  tone?: TriageTone
  value: ReactNode
}

function toneToken(tone: TriageTone): AppTone {
  if (tone === 'danger') return 'danger'
  if (tone === 'warning') return 'warning'
  if (tone === 'success') return 'success'
  return 'info'
}

export function TriageMetricCard({
  caption,
  label,
  tone = 'neutral',
  value,
}: TriageMetricCardProps) {
  const theme = useTheme()
  const token = theme.apiTesting.status[toneToken(tone)]

  return (
    <Card
      variant="outlined"
      sx={{
        height: '100%',
        overflow: 'hidden',
        position: 'relative',
        '&::before': {
          bgcolor: token.fg,
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
          <Typography component="div" sx={{ color: token.fg }} variant="h2">
            {value}
          </Typography>
          {caption ? (
            <Typography
              sx={{
                bgcolor: alpha(token.fg, theme.palette.mode === 'dark' ? 0.12 : 0.08),
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
