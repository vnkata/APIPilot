import AccountTreeIcon from '@mui/icons-material/AccountTree'
import BuildIcon from '@mui/icons-material/Build'
import CompareArrowsIcon from '@mui/icons-material/CompareArrows'
import CloseIcon from '@mui/icons-material/Close'
import {
  Button,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import type { ReactNode } from 'react'

import type { TourDefinition, TourId } from './productTourTypes'
import { TOUR_ANCHORS, tourAnchor } from './tourAnchors'

type OnboardingPath = {
  description: string
  href: string
  icon: ReactNode
  label: string
  tourId: TourId
}

type OnboardingPromptProps = {
  onDismiss: () => void
  onStartPath: (path: OnboardingPath) => void
  tour: TourDefinition
}

const onboardingPaths: OnboardingPath[] = [
  {
    description: 'Open the run catalog and learn how to inspect generated artifacts.',
    href: '/runs',
    icon: <AccountTreeIcon fontSize="small" />,
    label: 'Inspect an existing run',
    tourId: 'runs',
  },
  {
    description: 'Open Spec Manager and learn the write-flow from OpenAPI spec to dry-run execution.',
    href: '/builder/specs',
    icon: <BuildIcon fontSize="small" />,
    label: 'Build a new run',
    tourId: 'builder-specs',
  },
  {
    description: 'Open Compare Lab and learn how to explain artifact and JSON deltas.',
    href: '/compare',
    icon: <CompareArrowsIcon fontSize="small" />,
    label: 'Compare evidence',
    tourId: 'compare',
  },
]

export function OnboardingPrompt({ onDismiss, onStartPath, tour }: OnboardingPromptProps) {
  return (
    <Paper
      aria-label="New to APIPilot"
      elevation={0}
      role="region"
      sx={(theme) => ({
        bgcolor: theme.apiTesting.surface.elevated,
        border: '1px solid',
        borderColor: theme.apiTesting.border.strong,
        borderRadius: 1.5,
        bottom: 24,
        boxShadow: theme.apiTesting.shadow.floating,
        maxWidth: 560,
        p: 2,
        pointerEvents: 'none',
        position: 'fixed',
        right: 24,
        width: 'calc(100vw - 48px)',
        zIndex: theme.zIndex.modal - 1,
      })}
      {...tourAnchor(TOUR_ANCHORS.onboardingPaths)}
    >
      <Stack spacing={1.5}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start' }}>
          <Stack spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
            <Typography color="text.secondary" sx={{ fontWeight: 800 }} variant="caption">
              {tour.label}
            </Typography>
            <Typography component="h2" variant="h3">
              New to APIPilot?
            </Typography>
            <Typography color="text.secondary" variant="body2">
              Choose the workflow you want to learn first. Each option opens the right page and starts its guided tour.
            </Typography>
          </Stack>
          <Tooltip title="Dismiss onboarding">
            <IconButton aria-label="Dismiss onboarding" onClick={onDismiss} size="small" sx={{ pointerEvents: 'auto' }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>

        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1}>
          {onboardingPaths.map((path) => (
            <Button
              key={path.tourId}
              onClick={() => onStartPath(path)}
              startIcon={path.icon}
              sx={{
                alignItems: 'flex-start',
                justifyContent: 'flex-start',
                minHeight: 76,
                pointerEvents: 'auto',
                textAlign: 'left',
              }}
              variant={path.tourId === 'builder-specs' ? 'contained' : 'outlined'}
            >
              <Stack spacing={0.25}>
                <Typography component="span" sx={{ fontWeight: 800 }} variant="body2">
                  {path.label}
                </Typography>
                <Typography component="span" sx={{ whiteSpace: 'normal' }} variant="caption">
                  {path.description}
                </Typography>
              </Stack>
            </Button>
          ))}
        </Stack>
      </Stack>
    </Paper>
  )
}
