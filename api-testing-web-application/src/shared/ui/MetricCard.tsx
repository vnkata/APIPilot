import { Card, CardContent, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

type MetricCardProps = {
  caption?: ReactNode
  label: string
  value: ReactNode
}

export function MetricCard({ caption, label, value }: MetricCardProps) {
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Stack spacing={0.5}>
          <Typography color="text.secondary" variant="caption">
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
      </CardContent>
    </Card>
  )
}
