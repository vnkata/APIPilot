import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutlineOutlined'
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked'
import SkipNextIcon from '@mui/icons-material/SkipNext'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  type ChipProps,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material'
import { useEffect, useMemo } from 'react'

import { useAppDispatch, useAppSelector } from '../../../app/hooks'
import type {
  CombinationDetailResponse,
  CombinationReviewResponse,
} from '../../../shared/api/generated/model'
import { emitActivationOnboardingEvent } from '../../product-tour/activationOnboardingAnalytics'
import {
  completeActivationStep,
  dismissActivation,
  selectCombinationHitlActivationProgress,
  skipActivationStep,
  startActivation,
} from '../../product-tour/activationOnboardingSlice'
import type { CombinationHitlActivationStepId } from '../../product-tour/activationOnboardingTypes'
import {
  combinationHitlActivationEventBase,
  deriveCombinationHitlActivationModel,
  safeCombinationActivationMetadata,
  type CombinationHitlActivationRoute,
} from '../../product-tour/activationOnboardingViewModels'

type CombinationHitlActivationPanelProps = {
  detail?: CombinationDetailResponse
  review?: CombinationReviewResponse
  route: CombinationHitlActivationRoute
  runName: string
  selectedEligibleCombinationCount?: number
}

function stepStateColor(state: string): ChipProps['color'] {
  if (state === 'completed') return 'success'
  if (state === 'current') return 'warning'
  if (state === 'skipped') return 'default'
  return 'default'
}

function stepStateIcon(state: string) {
  if (state === 'completed') return <CheckCircleOutlineIcon fontSize="small" />
  if (state === 'skipped') return <SkipNextIcon fontSize="small" />
  return <RadioButtonUncheckedIcon fontSize="small" />
}

export function CombinationHitlActivationPanel({
  detail,
  review,
  route,
  runName,
  selectedEligibleCombinationCount = 0,
}: CombinationHitlActivationPanelProps) {
  const dispatch = useAppDispatch()
  const progress = useAppSelector((state) => selectCombinationHitlActivationProgress(state, runName))
  const metadata = useMemo(
    () => safeCombinationActivationMetadata({ detail, review }),
    [detail, review],
  )
  const model = deriveCombinationHitlActivationModel({
    detail,
    progress,
    review,
    route,
    selectedEligibleCombinationCount,
  })
  const visible = route === 'review_workspace' || !model.dismissed || model.active
  const nextStep = model.steps.find((step) => step.state === 'current')
  const completionValue = Math.round((model.completedCount / model.totalCount) * 100)

  function recordStepComplete(stepId: CombinationHitlActivationStepId) {
    if (progress?.completedStepIds[stepId]) return
    dispatch(completeActivationStep({ runName, stepId }))
    emitActivationOnboardingEvent({
      ...combinationHitlActivationEventBase(),
      metadata,
      stepId,
      type: 'step_completed',
    })
    if (stepId === 'finalize_decision') {
      emitActivationOnboardingEvent({
        ...combinationHitlActivationEventBase(),
        metadata,
        stepId,
        type: 'activation_completed',
      })
    }
  }

  useEffect(() => {
    if (route === 'review_workspace') {
      recordStepComplete('open_review_workspace')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route, runName])

  if (!visible) return null

  return (
    <Card aria-label="Combination HITL activation" role="region" variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ justifyContent: 'space-between' }}>
            <Stack spacing={0.5}>
              <Typography component="h2" variant="h2">
                Combination HITL activation
              </Typography>
              <Typography color="text.secondary" variant="body2">
                Follow the safe review path from eligible Combination row to human final decision.
              </Typography>
            </Stack>
            <Chip
              color={model.completed ? 'success' : 'default'}
              label={`${model.completedCount} of ${model.totalCount} complete`}
              variant="outlined"
            />
          </Stack>

          <LinearProgress
            aria-label="Combination HITL activation progress"
            value={completionValue}
            variant="determinate"
          />

          <Box
            sx={(theme) => ({
              border: '1px solid',
              borderColor: theme.apiTesting.border.default,
              borderRadius: 1,
              p: 1,
            })}
          >
            <Typography color="text.secondary" variant="body2">
              {model.active || route === 'review_workspace' || model.completed
                ? model.nextAction
                : 'Start here when you want APIPilot to guide one Combination row through draft, approval, evidence, and final decision.'}
            </Typography>
          </Box>

          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
            {model.steps.map((step) => (
              <Chip
                color={stepStateColor(step.state)}
                icon={stepStateIcon(step.state)}
                key={step.id}
                label={`${step.label}: ${step.state}`}
                size="small"
                variant={step.state === 'completed' ? 'filled' : 'outlined'}
              />
            ))}
          </Stack>

          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button
              onClick={() => {
                dispatch(startActivation({ runName }))
                emitActivationOnboardingEvent({
                  ...combinationHitlActivationEventBase(),
                  metadata,
                  type: 'onboarding_started',
                })
                recordStepComplete(route === 'combination_table' ? 'open_combination_table' : 'open_review_workspace')
              }}
              size="small"
              variant={model.active ? 'outlined' : 'contained'}
            >
              {model.active ? 'Resume HITL activation' : 'Start HITL activation'}
            </Button>
            {nextStep ? (
              <Button
                onClick={() => {
                  dispatch(skipActivationStep({ runName, stepId: nextStep.id }))
                  emitActivationOnboardingEvent({
                    ...combinationHitlActivationEventBase(),
                    metadata,
                    stepId: nextStep.id,
                    type: 'step_skipped',
                  })
                }}
                size="small"
                variant="outlined"
              >
                Skip step
              </Button>
            ) : null}
            <Button
              onClick={() => {
                dispatch(dismissActivation({ runName }))
                emitActivationOnboardingEvent({
                  ...combinationHitlActivationEventBase(),
                  metadata,
                  type: 'checklist_dismissed',
                })
              }}
              size="small"
              variant="text"
            >
              Dismiss checklist
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}
