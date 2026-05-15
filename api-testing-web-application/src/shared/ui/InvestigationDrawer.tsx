import CloseIcon from '@mui/icons-material/Close'
import {
  Box,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import type { ReactNode } from 'react'

import { ApiErrorAlert } from './ApiErrorAlert'
import { PageSkeleton } from './PageSkeleton'

type InvestigationDrawerProps = {
  ariaLabel: string
  children?: ReactNode
  error?: unknown
  isError?: boolean
  isLoading?: boolean
  onClose: () => void
  onRetry?: () => void
  open: boolean
  subtitle?: ReactNode
  title: ReactNode
}

export function InvestigationDrawer({
  ariaLabel,
  children,
  error,
  isError = false,
  isLoading = false,
  onClose,
  onRetry,
  open,
  subtitle,
  title,
}: InvestigationDrawerProps) {
  return (
    <Drawer
      anchor="right"
      onClose={onClose}
      open={open}
      slotProps={{ paper: { sx: { maxWidth: '100%', width: { xs: '100%', sm: 560 } } } }}
      variant="persistent"
    >
      <Box aria-label={ariaLabel} role="dialog" sx={{ height: '100%', overflow: 'auto', p: 2 }}>
        <Stack spacing={2}>
          <Stack direction="row" sx={{ alignItems: 'flex-start', gap: 1 }}>
            <Stack spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
              <Typography component="h2" variant="h3">
                {title}
              </Typography>
              {subtitle ? (
                <Typography color="text.secondary" sx={{ wordBreak: 'break-word' }} variant="body2">
                  {subtitle}
                </Typography>
              ) : null}
            </Stack>
            <Tooltip title={`Close ${ariaLabel.toLowerCase()}`}>
              <IconButton aria-label={`Close ${ariaLabel.toLowerCase()}`} onClick={onClose} size="small">
                <CloseIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>
          <Divider />
          {isLoading ? <PageSkeleton /> : null}
          {isError ? <ApiErrorAlert error={error} onRetry={onRetry} /> : null}
          {!isLoading && !isError ? children : null}
        </Stack>
      </Box>
    </Drawer>
  )
}
