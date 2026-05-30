import CloseIcon from '@mui/icons-material/Close'
import {
  Box,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
  type BoxProps,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { useEffect, useRef, type KeyboardEvent, type ReactNode } from 'react'

import { ApiErrorAlert } from './ApiErrorAlert'
import { PageSkeleton } from './PageSkeleton'

type InvestigationDrawerProps = Omit<BoxProps, 'children' | 'title'> & {
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
  sx,
  ...props
}: InvestigationDrawerProps) {
  const theme = useTheme()
  const desktop = useMediaQuery(theme.breakpoints.up('md'), { defaultMatches: true })
  const returnFocusRef = useRef<HTMLElement | null>(null)
  const role = desktop ? 'complementary' : 'dialog'

  useEffect(() => {
    if (open && !returnFocusRef.current) {
      returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    }

    if (!open && returnFocusRef.current) {
      const element = returnFocusRef.current
      returnFocusRef.current = null
      window.setTimeout(() => {
        if (document.contains(element)) {
          element.focus()
        }
      }, 0)
    }
  }, [open])

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.stopPropagation()
      onClose()
    }
  }

  return (
    <Drawer
      anchor="right"
      onClose={onClose}
      open={open}
      slotProps={{
        paper: {
          sx: {
            maxWidth: '100%',
            width: { xs: '100%', sm: 560 },
          },
        },
      }}
      variant={desktop ? 'persistent' : 'temporary'}
    >
      <Box
        aria-label={ariaLabel}
        onKeyDown={handleKeyDown}
        role={role}
        sx={[{ height: '100%', overflow: 'auto', p: 2 }, ...(sx ? (Array.isArray(sx) ? sx : [sx]) : [])]}
        tabIndex={-1}
        {...props}
      >
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
