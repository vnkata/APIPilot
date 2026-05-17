import { Chip, Stack, Typography } from '@mui/material'

type SignalTone = 'danger' | 'neutral' | 'success' | 'warning'

type StatusSignal = {
  label: string
  tone?: SignalTone
  value: string | number
}

type StatusSignalStripProps = {
  ariaLabel: string
  signals: StatusSignal[]
}

function chipColor(tone: SignalTone | undefined) {
  if (tone === 'danger') return 'error'
  if (tone === 'warning') return 'warning'
  if (tone === 'success') return 'success'
  return 'default'
}

export function StatusSignalStrip({ ariaLabel, signals }: StatusSignalStripProps) {
  return (
    <Stack
      aria-label={ariaLabel}
      direction="row"
      role="list"
      sx={{ flexWrap: 'wrap', gap: 1 }}
    >
      {signals.map((signal) => (
        <Chip
          color={chipColor(signal.tone)}
          key={signal.label}
          label={
            <Typography component="span" variant="caption">
              {signal.label}: {signal.value}
            </Typography>
          }
          role="listitem"
          size="small"
          variant="outlined"
        />
      ))}
    </Stack>
  )
}
