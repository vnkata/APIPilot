import CloseIcon from '@mui/icons-material/Close'
import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined'
import { Button, IconButton, Paper, Stack, Tooltip, Typography } from '@mui/material'

import type { TourDefinition } from './productTourTypes'

type TourPromptProps = {
  onDismiss: () => void
  onStart: () => void
  tour: TourDefinition
}

export function TourPrompt({ onDismiss, onStart, tour }: TourPromptProps) {
  return (
    <Paper
      aria-label={`${tour.label} prompt`}
      elevation={0}
      role="region"
      sx={(theme) => ({
        backgroundImage: theme.apiTesting.gradient.panel,
        border: '1px solid',
        borderColor: theme.apiTesting.border.strong,
        borderRadius: 1.5,
        bottom: { xs: 16, md: 'auto' },
        boxShadow: theme.apiTesting.shadow.floating,
        maxWidth: 420,
        p: 1.5,
        pointerEvents: 'none',
        position: 'fixed',
        right: { xs: 16, md: 24 },
        top: { xs: 'auto', md: 88 },
        width: { xs: 'calc(100vw - 32px)', sm: 420 },
        zIndex: theme.zIndex.modal - 1,
      })}
    >
      <Stack direction="row" spacing={1.25} sx={{ alignItems: 'flex-start' }}>
        <HelpOutlineIcon color="primary" fontSize="small" sx={{ mt: 0.25 }} />
        <Stack spacing={0.75} sx={{ flex: 1, minWidth: 0 }}>
          <Typography sx={{ fontWeight: 800 }} variant="subtitle2">
            Need a quick orientation?
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Take the {tour.label.toLowerCase()} to learn the fastest QA/QC path through this page.
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button onClick={onStart} size="small" sx={{ pointerEvents: 'auto' }} variant="contained">
              Start tour
            </Button>
            <Button onClick={onDismiss} size="small" sx={{ pointerEvents: 'auto' }}>
              Not now
            </Button>
          </Stack>
        </Stack>
        <Tooltip title="Dismiss tour prompt">
          <IconButton aria-label="Dismiss tour prompt" onClick={onDismiss} size="small" sx={{ pointerEvents: 'auto' }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
    </Paper>
  )
}
