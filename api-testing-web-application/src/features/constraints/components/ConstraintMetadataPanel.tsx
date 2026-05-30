import { Grid, Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

import { Panel } from '../../../shared/ui/Panel'

type MetadataItem = {
  label: string
  value: ReactNode
}

type ConstraintMetadataPanelProps = {
  badges: ReactNode
  items: MetadataItem[]
  title: string
}

export function ConstraintMetadataPanel({
  badges,
  items,
  title,
}: ConstraintMetadataPanelProps) {
  return (
    <Panel sx={{ p: 1.5 }} title={title}>
      <Stack spacing={1.25}>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
          {badges}
        </Stack>
        <Grid container spacing={1.25}>
          {items.map((item) => (
            <Grid key={item.label} size={{ xs: 12, sm: 6 }}>
              <Stack spacing={0.25}>
                <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
                  {item.label}
                </Typography>
                <Typography component="div" sx={{ overflowWrap: 'anywhere' }} variant="body2">
                  {item.value}
                </Typography>
              </Stack>
            </Grid>
          ))}
        </Grid>
      </Stack>
    </Panel>
  )
}
