import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import {
  Divider,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material'
import { useState } from 'react'

import { useAppDispatch } from '../../app/hooks'
import { navigateInApp } from '../../shared/lib/navigation'
import { emitActivationOnboardingEvent } from './activationOnboardingAnalytics'
import { startActivation } from './activationOnboardingSlice'
import { combinationHitlActivationEventBase } from './activationOnboardingViewModels'
import { resetTourProgress, startTour } from './productTourSlice'
import type { TourId } from './productTourTypes'
import { availableTourIds, tourLabel } from './tourRegistry'
import { TOUR_ANCHORS, tourAnchor } from './tourAnchors'

type TourHelpMenuProps = {
  pathname: string
}

function runNameFromPathname(pathname: string) {
  const encodedRunName = pathname.match(/^\/runs\/([^/]+)/)?.[1]
  return encodedRunName ? decodeURIComponent(encodedRunName) : undefined
}

function supportsCombinationHitlActivation(pathname: string) {
  return /^\/runs\/[^/]+\/constraints(?:\/combination\/[^/]+\/review)?\/?$/.test(pathname)
}

export function TourHelpMenu({ pathname }: TourHelpMenuProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const dispatch = useAppDispatch()
  const open = Boolean(anchorEl)
  const availableTours = availableTourIds(pathname)
  const activationRunName = supportsCombinationHitlActivation(pathname)
    ? runNameFromPathname(pathname)
    : undefined

  function handleStartTour(tourId: TourId) {
    dispatch(startTour({ tourId }))
    setAnchorEl(null)
  }

  function handleStartCombinationHitlActivation() {
    if (!activationRunName) return
    dispatch(startActivation({ runName: activationRunName }))
    emitActivationOnboardingEvent({
      ...combinationHitlActivationEventBase(),
      type: 'onboarding_started',
    })
    navigateInApp(`/runs/${encodeURIComponent(activationRunName)}/constraints?constraintTab=combination&constraintsView=table`)
    setAnchorEl(null)
  }

  return (
    <>
      <Tooltip title="Open guided tours">
        <IconButton
          aria-controls={open ? 'guided-tour-menu' : undefined}
          aria-expanded={open ? 'true' : undefined}
          aria-haspopup="menu"
          aria-label="Open guided tours"
          onClick={(event) => setAnchorEl(event.currentTarget)}
          size="small"
          {...tourAnchor(TOUR_ANCHORS.appHelp)}
        >
          <HelpOutlineIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        id="guided-tour-menu"
        onClose={() => setAnchorEl(null)}
        open={open}
      >
        {availableTours.map((tourId) => (
          <MenuItem key={tourId} onClick={() => handleStartTour(tourId)}>
            <ListItemText primary={`Start ${tourLabel(tourId)}`} />
          </MenuItem>
        ))}
        {activationRunName ? (
          <MenuItem onClick={handleStartCombinationHitlActivation}>
            <ListItemText primary="Start Combination HITL activation" />
          </MenuItem>
        ) : null}
        <Divider />
        <MenuItem
          onClick={() => {
            dispatch(resetTourProgress(undefined))
            setAnchorEl(null)
          }}
        >
          <ListItemIcon>
            <RestartAltIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="Reset tour progress" />
        </MenuItem>
      </Menu>
    </>
  )
}
