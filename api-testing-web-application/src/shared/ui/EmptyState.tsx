import { Box, Typography } from '@mui/material'

type EmptyStateProps = {
  description?: string
  title: string
}

export function EmptyState({ description, title }: EmptyStateProps) {
  return (
    <Box
      sx={{
        alignItems: 'center',
        border: '1px dashed',
        borderColor: 'divider',
        borderRadius: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 160,
        justifyContent: 'center',
        p: 3,
        textAlign: 'center',
      }}
    >
      <Typography variant="h3">{title}</Typography>
      {description ? (
        <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 560 }}>
          {description}
        </Typography>
      ) : null}
    </Box>
  )
}
