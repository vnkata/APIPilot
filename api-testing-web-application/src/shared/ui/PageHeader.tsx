import { Stack, Typography, type StackProps } from '@mui/material'
import type { ReactNode } from 'react'

type PageHeaderProps = Omit<StackProps, 'title'> & {
  actions?: ReactNode
  eyebrow?: string
  subtitle?: ReactNode
  title: ReactNode
}

export function PageHeader({ actions, eyebrow, subtitle, title, sx, ...props }: PageHeaderProps) {
  return (
    <Stack
      direction={{ xs: 'column', md: 'row' }}
      spacing={2}
      sx={[{ justifyContent: 'space-between', mb: 2 }, ...(sx ? (Array.isArray(sx) ? sx : [sx]) : [])]}
      {...props}
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
