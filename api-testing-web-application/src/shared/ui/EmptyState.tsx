import { Box, Typography } from '@mui/material'
import type { ReactNode } from 'react'

type EmptyStateProps = {
  action?: ReactNode
  description?: string
  title: string
}

export function EmptyState({ action, description, title }: EmptyStateProps) {
  return (
    <Box
      sx={{
        alignItems: 'center',
        border: '1px dashed',
        borderColor: (theme) => theme.apiTesting.border.strong,
        borderRadius: 1.5,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        minHeight: 160,
        justifyContent: 'center',
        p: { xs: 3, md: 4 },
        textAlign: 'center',
      }}
    >
      <Typography variant="h3">{title}</Typography>
      {description ? (
        <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 560 }}>
          {description}
        </Typography>
      ) : null}
      {action}
    </Box>
  )
}
