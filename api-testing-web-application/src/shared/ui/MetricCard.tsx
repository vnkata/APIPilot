import { Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

import { Panel } from './Panel'

type MetricCardProps = {
  caption?: ReactNode
  label: string
  value: ReactNode
}

export function MetricCard({ caption, label, value }: MetricCardProps) {
  return (
    <Panel sx={{ height: '100%' }}>
      <Stack spacing={0.5}>
        <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
          {label}
        </Typography>
        <Typography component="div" variant="h2">
          {value}
        </Typography>
        {caption ? (
          <Typography color="text.secondary" variant="body2">
            {caption}
          </Typography>
        ) : null}
      </Stack>
    </Panel>
  )
}
