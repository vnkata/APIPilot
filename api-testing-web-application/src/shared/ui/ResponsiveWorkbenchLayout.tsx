import { Box, Grid } from '@mui/material'
import type { ReactNode } from 'react'

type ResponsiveWorkbenchLayoutProps = {
  detail: ReactNode
  sidebar: ReactNode
}

export function ResponsiveWorkbenchLayout({ detail, sidebar }: ResponsiveWorkbenchLayoutProps) {
  return (
    <Grid container spacing={2}>
      <Grid size={{ xs: 12, lg: 4, xl: 3 }}>
        <Box sx={{ height: '100%' }}>{sidebar}</Box>
      </Grid>
      <Grid size={{ xs: 12, lg: 8, xl: 9 }}>
        {detail}
      </Grid>
    </Grid>
  )
}
