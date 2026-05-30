import { Paper, Stack, Typography, type PaperProps } from '@mui/material'
import type { ReactNode } from 'react'

type PanelProps = Omit<PaperProps, 'title'> & {
  actions?: ReactNode
  children: ReactNode
  subtitle?: ReactNode
  title?: ReactNode
}

export function Panel({ actions, children, subtitle, sx, title, ...props }: PanelProps) {
  return (
    <Paper
      elevation={0}
      sx={[
        (theme) => ({
          backgroundImage: theme.apiTesting.gradient.panel,
          border: '1px solid',
          borderColor: theme.apiTesting.border.default,
          borderRadius: 1.5,
          boxShadow: theme.apiTesting.shadow.panel,
          minWidth: 0,
          p: 2,
          transition: theme.apiTesting.motion.transition.panel,
          '@media (prefers-reduced-motion: reduce)': {
            transition: 'none',
          },
        }),
        ...(sx ? (Array.isArray(sx) ? sx : [sx]) : []),
      ]}
      {...props}
    >
      {title || actions || subtitle ? (
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1.5}
          sx={{ alignItems: { sm: 'flex-start' }, justifyContent: 'space-between', mb: 2 }}
        >
          <Stack spacing={0.5} sx={{ minWidth: 0 }}>
            {title ? (
              <Typography component="h2" variant="h3">
                {title}
              </Typography>
            ) : null}
            {subtitle ? (
              <Typography color="text.secondary" variant="body2">
                {subtitle}
              </Typography>
            ) : null}
          </Stack>
          {actions ? <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>{actions}</Stack> : null}
        </Stack>
      ) : null}
      {children}
    </Paper>
  )
}
