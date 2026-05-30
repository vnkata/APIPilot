import { Stack } from '@mui/material'
import type { ReactNode } from 'react'

import { Panel } from './Panel'

type FilterToolbarProps = {
  children: ReactNode
}

export function FilterToolbar({ children }: FilterToolbarProps) {
  return (
    <Panel sx={{ p: 1.5 }}>
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
    </Panel>
  )
}
