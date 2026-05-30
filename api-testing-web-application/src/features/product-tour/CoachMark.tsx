import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import ArrowForwardIcon from '@mui/icons-material/ArrowForward'
import CloseIcon from '@mui/icons-material/Close'
import LaunchIcon from '@mui/icons-material/Launch'
import {
  Box,
  Button,
  IconButton,
  LinearProgress,
  Paper,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'

import type { TourDefinition, TourStep } from './productTourTypes'

type CoachMarkProps = {
  onAction: (step: TourStep) => void
  onBack: () => void
  onClose: () => void
  onNext: () => void
  rect: DOMRect | null
  step: TourStep
  stepIndex: number
  tour: TourDefinition
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function coachPosition(rect: DOMRect | null) {
  const width = 360
  const gap = 18
  const margin = 16

  if (!rect) {
    return {
      left: `calc(50vw - ${width / 2}px)`,
      top: '50%',
      transform: 'translateY(-50%)',
      width,
    }
  }

  const below = rect.bottom + gap
  const above = rect.top - gap - 220
  const top = below + 240 < window.innerHeight ? below : Math.max(above, margin)
  const left = clamp(rect.left + rect.width / 2 - width / 2, margin, window.innerWidth - width - margin)

  return { left, top, width }
}

export function CoachMark({
  onAction,
  onBack,
  onClose,
  onNext,
  rect,
  step,
  stepIndex,
  tour,
}: CoachMarkProps) {
  const theme = useTheme()
  const mobile = useMediaQuery(theme.breakpoints.down('sm'))
  const isFirst = stepIndex === 0
  const isLast = stepIndex === tour.steps.length - 1
  const progress = ((stepIndex + 1) / tour.steps.length) * 100
  const desktopPosition = coachPosition(rect)

  return (
    <Paper
      aria-describedby="product-tour-step-description"
      aria-labelledby="product-tour-step-title"
      elevation={0}
      role="dialog"
      sx={(muiTheme) => ({
        backgroundImage: muiTheme.apiTesting.gradient.panel,
        border: '1px solid',
        borderColor: muiTheme.apiTesting.border.strong,
        borderRadius: 1.5,
        bottom: mobile ? 0 : 'auto',
        boxShadow: muiTheme.apiTesting.shadow.floating,
        left: mobile ? 0 : desktopPosition.left,
        maxHeight: mobile ? '70vh' : 'min(76vh, 520px)',
        maxWidth: mobile ? '100%' : desktopPosition.width,
        overflow: 'auto',
        p: 2,
        position: 'fixed',
        right: mobile ? 0 : 'auto',
        top: mobile ? 'auto' : desktopPosition.top,
        transform: mobile ? 'none' : desktopPosition.transform,
        width: mobile ? '100%' : desktopPosition.width,
        zIndex: muiTheme.zIndex.modal + 1,
      })}
    >
      <Stack spacing={1.5}>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'flex-start' }}>
          <Stack spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
            <Typography color="text.secondary" sx={{ fontWeight: 800 }} variant="caption">
              {tour.label} · Step {stepIndex + 1} of {tour.steps.length}
            </Typography>
            <Typography id="product-tour-step-title" variant="h3">
              {step.title}
            </Typography>
          </Stack>
          <Tooltip title="Close tour">
            <IconButton aria-label="Close tour" onClick={onClose} size="small">
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>

        <LinearProgress aria-label="Tour progress" value={progress} variant="determinate" />

        <Typography color="text.secondary" id="product-tour-step-description" variant="body2">
          {step.body}
        </Typography>

        {!rect ? (
          <Typography color="warning.main" variant="caption">
            This tour target is not visible in the current layout. You can continue the tour or use the page normally.
          </Typography>
        ) : null}

        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          spacing={1}
          sx={{ justifyContent: 'space-between' }}
        >
          <Box>
            {step.action ? (
              <Button
                onClick={() => onAction(step)}
                size="small"
                startIcon={<LaunchIcon fontSize="small" />}
                variant="outlined"
              >
                {step.action.label}
              </Button>
            ) : null}
          </Box>
          <Stack direction="row" spacing={1} sx={{ justifyContent: 'flex-end' }}>
            <Button disabled={isFirst} onClick={onBack} size="small" startIcon={<ArrowBackIcon />}>
              Back
            </Button>
            <Button onClick={onNext} size="small" endIcon={!isLast ? <ArrowForwardIcon /> : undefined} variant="contained">
              {isLast ? 'Finish' : 'Next'}
            </Button>
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  )
}
