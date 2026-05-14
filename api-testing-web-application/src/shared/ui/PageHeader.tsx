import { Stack, Typography } from '@mui/material'
import type { ReactNode } from 'react'

type PageHeaderProps = {
  actions?: ReactNode
  eyebrow?: string
  subtitle?: ReactNode
  title: ReactNode
}

export function PageHeader({ actions, eyebrow, subtitle, title }: PageHeaderProps) {
  return (
    <Stack
      direction={{ xs: 'column', md: 'row' }}
      spacing={2}
      sx={{ justifyContent: 'space-between', mb: 2 }}
    >
      <Stack spacing={0.5}>
        {eyebrow ? (
          <Typography color="text.secondary" variant="caption">
            {eyebrow}
          </Typography>
        ) : null}
        <Typography component="h1" variant="h1">
          {title}
        </Typography>
        {subtitle ? (
          <Typography color="text.secondary" variant="body2">
            {subtitle}
          </Typography>
        ) : null}
      </Stack>
      {actions ? <Stack direction="row" spacing={1}>{actions}</Stack> : null}
    </Stack>
  )
}
