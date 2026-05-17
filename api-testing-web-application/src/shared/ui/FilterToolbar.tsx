import { Paper, Stack } from '@mui/material'
import type { ReactNode } from 'react'

type FilterToolbarProps = {
  children: ReactNode
}

export function FilterToolbar({ children }: FilterToolbarProps) {
  return (
    <Paper
      component={Stack}
      spacing={1.5}
      sx={{
        bgcolor: 'background.paper',
        borderColor: 'divider',
        p: 1.5,
      }}
      variant="outlined"
    >
      <Stack
        direction={{ xs: 'column', md: 'row' }}
        spacing={0}
        sx={{
          flexWrap: 'wrap',
          gap: 1.5,
          '& > *': {
            maxWidth: '100%',
          },
        }}
      >
        {children}
      </Stack>
    </Paper>
  )
}
