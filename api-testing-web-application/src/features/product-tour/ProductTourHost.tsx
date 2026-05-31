import { Box, Modal } from '@mui/material'
import { useLocation } from '@tanstack/react-router'
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'

import { useAppDispatch, useAppSelector } from '../../app/hooks'
import { navigateInApp } from '../../shared/lib/navigation'
import { CoachMark } from './CoachMark'
import { emitTourEvent } from './tourAnalytics'
import { OnboardingPrompt } from './OnboardingPrompt'
import {
  completeTour,
  dismissPrompt,
  nextStep,
  previousStep,
  selectProductTour,
  setPromptTour,
  skipTour,
  startTour,
} from './productTourSlice'
import type { TourDefinition, TourId, TourStep } from './productTourTypes'
import { currentPageTourId, loadTourDefinition } from './tourRegistry'
import { SpotlightFrame } from './SpotlightFrame'
import { TourPrompt } from './TourPrompt'
import { useTourTargetRect } from './useTourTargetRect'

function encodedRunName(pathname: string) {
  return pathname.match(/^\/runs\/([^/]+)/)?.[1]
}

function resolveActionHref(href: string, pathname: string) {
  return href.replace('{runName}', encodedRunName(pathname) ?? '')
}

export function ProductTourHost() {
  const { pathname } = useLocation()
  const dispatch = useAppDispatch()
  const tourState = useAppSelector(selectProductTour)
  const [definitions, setDefinitions] = useState<Partial<Record<TourId, TourDefinition>>>({})
  const activeTour = tourState.activeTourId ? definitions[tourState.activeTourId] : undefined
  const promptTour = tourState.promptTourId ? definitions[tourState.promptTourId] : undefined
  const onboardingTour = definitions.onboarding
  const activeStep = activeTour?.steps[tourState.activeStepIndex]
  const targetState = useTourTargetRect(activeStep?.anchorId, Boolean(activeStep))
  const returnFocusRef = useRef<HTMLElement | null>(null)
  const lastStartedRef = useRef<string | undefined>(undefined)
  const lastViewedRef = useRef<string | undefined>(undefined)

  const pageTourId = useMemo(() => currentPageTourId(pathname), [pathname])
  const shouldConsiderOnboarding = pathname === '/runs' && !tourState.activeTourId && !tourState.promptTourId

  useEffect(() => {
    if (
      !pageTourId ||
      !tourState.promptTourId ||
      tourState.promptTourId === pageTourId ||
      tourState.activeTourId
    ) {
      return
    }

    dispatch(setPromptTour({ tourId: undefined }))
  }, [dispatch, pageTourId, tourState.activeTourId, tourState.promptTourId])

  useEffect(() => {
    const ids = new Set<TourId>()
    if (pageTourId) ids.add(pageTourId)
    if (shouldConsiderOnboarding) ids.add('onboarding')
    if (tourState.activeTourId) ids.add(tourState.activeTourId)
    if (tourState.promptTourId) ids.add(tourState.promptTourId)

    ids.forEach((tourId) => {
      if (definitions[tourId]) return
      void loadTourDefinition(tourId).then((definition) => {
        setDefinitions((current) => ({ ...current, [definition.id]: definition }))
      })
    })
  }, [definitions, pageTourId, shouldConsiderOnboarding, tourState.activeTourId, tourState.promptTourId])

  useEffect(() => {
    if (!pageTourId || tourState.activeTourId || tourState.promptTourId) return

    const definition = definitions[pageTourId]
    if (!definition || !definition.roles.includes(tourState.role)) return

    const completedVersion = tourState.progressByTourId[pageTourId]?.completedVersion
    const dismissedVersion = tourState.dismissedPromptByTourId[pageTourId]
    const promptAlreadyHandled =
      completedVersion === definition.version || dismissedVersion === definition.version

    if (!promptAlreadyHandled) {
      dispatch(setPromptTour({ tourId: pageTourId }))
      emitTourEvent({
        tourId: pageTourId,
        type: 'prompt_shown',
        version: definition.version,
      })
    }
  }, [
    definitions,
    dispatch,
    pageTourId,
    tourState.activeTourId,
    tourState.dismissedPromptByTourId,
    tourState.progressByTourId,
    tourState.promptTourId,
    tourState.role,
  ])

  const showOnboardingPrompt = useMemo(() => {
    if (!shouldConsiderOnboarding || !onboardingTour) return false
    const completedVersion = tourState.progressByTourId.onboarding?.completedVersion
    const dismissedVersion = tourState.dismissedPromptByTourId.onboarding
    return completedVersion !== onboardingTour.version && dismissedVersion !== onboardingTour.version
  }, [
    onboardingTour,
    shouldConsiderOnboarding,
    tourState.dismissedPromptByTourId,
    tourState.progressByTourId,
  ])

  useEffect(() => {
    if (!activeTour || !tourState.activeTourId) return
    const key = `${activeTour.id}:${activeTour.version}`
    if (lastStartedRef.current === key) return
    lastStartedRef.current = key
    emitTourEvent({
      tourId: activeTour.id,
      type: 'tour_started',
      version: activeTour.version,
    })
  }, [activeTour, tourState.activeTourId])

  useEffect(() => {
    if (!activeTour || !activeStep) return
    const key = `${activeTour.id}:${activeTour.version}:${activeStep.id}:${tourState.activeStepIndex}`
    if (lastViewedRef.current === key) return
    lastViewedRef.current = key
    emitTourEvent({
      stepId: activeStep.id,
      stepIndex: tourState.activeStepIndex,
      tourId: activeTour.id,
      type: 'step_viewed',
      version: activeTour.version,
    })
  }, [activeStep, activeTour, tourState.activeStepIndex])

  useEffect(() => {
    if (activeTour && !returnFocusRef.current) {
      returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    }

    if (!activeTour && returnFocusRef.current) {
      const element = returnFocusRef.current
      returnFocusRef.current = null
      window.setTimeout(() => {
        if (document.contains(element)) element.focus()
      }, 0)
    }
  }, [activeTour])

  function handleClose() {
    if (!activeTour) return
    dispatch(skipTour({
      stepIndex: tourState.activeStepIndex,
      tourId: activeTour.id,
      version: activeTour.version,
    }))
    emitTourEvent({
      stepId: activeStep?.id,
      tourId: activeTour.id,
      type: 'tour_skipped',
      version: activeTour.version,
    })
  }

  function handleNext() {
    if (!activeTour) return
    if (tourState.activeStepIndex >= activeTour.steps.length - 1) {
      dispatch(completeTour({
        stepIndex: tourState.activeStepIndex,
        tourId: activeTour.id,
        version: activeTour.version,
      }))
      emitTourEvent({
        tourId: activeTour.id,
        type: 'tour_completed',
        version: activeTour.version,
      })
      return
    }

    dispatch(nextStep({ maxStepIndex: activeTour.steps.length - 1 }))
  }

  function handleAction(step: TourStep) {
    if (!activeTour || !step.action?.href) return
    emitTourEvent({
      stepId: step.id,
      stepIndex: tourState.activeStepIndex,
      tourId: activeTour.id,
      type: 'step_action_clicked',
      version: activeTour.version,
    })
    navigateInApp(resolveActionHref(step.action.href, pathname))
  }

  function handleOnboardingPath(path: { href: string; tourId: TourId }) {
    if (!onboardingTour) return
    dispatch(dismissPrompt({ tourId: onboardingTour.id, version: onboardingTour.version }))
    navigateInApp(path.href)
    dispatch(startTour({ tourId: path.tourId }))
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape') {
      event.stopPropagation()
      handleClose()
    }
    if (event.key === 'ArrowRight' || event.key === 'Enter') {
      event.preventDefault()
      handleNext()
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault()
      dispatch(previousStep())
    }
  }

  return (
    <>
      {promptTour ? (
        <TourPrompt
          onDismiss={() => dispatch(dismissPrompt({ tourId: promptTour.id, version: promptTour.version }))}
          onStart={() => dispatch(startTour({ tourId: promptTour.id }))}
          tour={promptTour}
        />
      ) : null}

      {!promptTour && showOnboardingPrompt && onboardingTour ? (
        <OnboardingPrompt
          onDismiss={() => dispatch(dismissPrompt({ tourId: onboardingTour.id, version: onboardingTour.version }))}
          onStartPath={handleOnboardingPath}
          tour={onboardingTour}
        />
      ) : null}

      <Modal
        aria-labelledby="product-tour-step-title"
        hideBackdrop
        onClose={handleClose}
        open={Boolean(activeTour && activeStep)}
      >
        <Box onKeyDown={handleKeyDown} sx={{ outline: 'none' }} tabIndex={-1}>
          <SpotlightFrame rect={targetState.rect} />
          {activeTour && activeStep ? (
            <CoachMark
              onAction={handleAction}
              onBack={() => dispatch(previousStep())}
              onClose={handleClose}
              onNext={handleNext}
              rect={targetState.rect}
              step={activeStep}
              stepIndex={tourState.activeStepIndex}
              tour={activeTour}
            />
          ) : null}
        </Box>
      </Modal>
    </>
  )
}
