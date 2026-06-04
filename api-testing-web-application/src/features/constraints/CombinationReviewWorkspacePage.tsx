import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { Button, Stack, Typography } from '@mui/material'
import { useState } from 'react'

import { useAppDispatch } from '../../app/hooks'
import type {
  CombinationReviewFinalizeRequest,
  CounterExampleGenerateRequest,
  CounterExampleRunRequest,
  JsonValue,
} from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { PageLearningPanel } from '../../shared/ui/Guidance'
import { QueryState } from '../../shared/ui/QueryState'
import { emitActivationOnboardingEvent } from '../product-tour/activationOnboardingAnalytics'
import { completeActivationStep } from '../product-tour/activationOnboardingSlice'
import type { CombinationHitlActivationStepId } from '../product-tour/activationOnboardingTypes'
import {
  combinationHitlActivationEventBase,
  safeCombinationActivationMetadata,
} from '../product-tour/activationOnboardingViewModels'
import { CombinationDetailComposer } from './components/CombinationDetailComposer'
import { CombinationHitlActivationPanel } from './components/CombinationHitlActivationPanel'
import {
  useCombinationDetail,
  useCombinationReview,
  useFinalizeCombinationReview,
  useGenerateCounterExamples,
  useReopenCombinationReview,
  useRunCounterExamples,
  useUpdateCounterExampleCase,
} from './api'

type CombinationReviewWorkspacePageProps = {
  combinationId: string
  runName: string
}

export function CombinationReviewWorkspacePage({
  combinationId,
  runName,
}: CombinationReviewWorkspacePageProps) {
  const dispatch = useAppDispatch()
  const [detailView, setDetailView] = useState<'raw' | 'readable'>('readable')
  const encodedRunName = encodeRoutePart(runName)
  const detailQuery = useCombinationDetail(runName, combinationId)
  const reviewQuery = useCombinationReview(runName, combinationId)

  function refetchReviewSurface() {
    void detailQuery.refetch()
    void reviewQuery.refetch()
  }

  function recordActivationStep(stepId: CombinationHitlActivationStepId) {
    const metadata = safeCombinationActivationMetadata({
      detail: detailQuery.data,
      review: reviewQuery.data,
    })
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

  const generateCounterExamplesMutation = useGenerateCounterExamples({
    mutation: {
      onSuccess: () => {
        refetchReviewSurface()
        recordActivationStep('generate_draft')
      },
    },
  })
  const updateCounterExampleCaseMutation = useUpdateCounterExampleCase({
    mutation: {
      onSuccess: (_response, variables) => {
        refetchReviewSurface()
        if (variables.data.case_state === 'APPROVED') {
          recordActivationStep('approve_case')
        }
      },
    },
  })
  const runCounterExamplesMutation = useRunCounterExamples({
    mutation: {
      onSuccess: () => {
        refetchReviewSurface()
        recordActivationStep('run_evidence')
      },
    },
  })
  const finalizeReviewMutation = useFinalizeCombinationReview({
    mutation: {
      onSuccess: () => {
        refetchReviewSurface()
        recordActivationStep('finalize_decision')
      },
    },
  })
  const reopenReviewMutation = useReopenCombinationReview({
    mutation: { onSuccess: refetchReviewSurface },
  })

  function handleGenerateCounterExamples(data: CounterExampleGenerateRequest) {
    generateCounterExamplesMutation.mutate({ runName, combinationId, data })
  }

  function handleUpdateCounterExampleCase(
    caseId: string,
    caseState: string,
    rationale: string,
    request?: JsonValue | null,
  ) {
    updateCounterExampleCaseMutation.mutate({
      runName,
      combinationId,
      caseId,
      data: { case_state: caseState, rationale, request },
    })
  }

  function handleRunApprovedCounterExamples(data: CounterExampleRunRequest) {
    runCounterExamplesMutation.mutate({ runName, combinationId, data })
  }

  function handleFinalizeReview(data: CombinationReviewFinalizeRequest) {
    finalizeReviewMutation.mutate({ runName, combinationId, data })
  }

  function handleReopenReview(rationale: string) {
    reopenReviewMutation.mutate({ runName, combinationId, data: { rationale } })
  }

  const selectedOperationId = detailQuery.data?.operation_id
  const encodedOperationId = encodeURIComponent(selectedOperationId ?? '')
  const evidenceLinks = selectedOperationId
    ? [
        { href: `/runs/${encodedRunName}/graph?operationId=${encodedOperationId}`, label: 'Graph' },
        { href: `/runs/${encodedRunName}/test-cases?operationId=${encodedOperationId}`, label: 'Test cases' },
        { href: `/runs/${encodedRunName}/reports?operationId=${encodedOperationId}`, label: 'Reports' },
      ]
    : []
  const reviewActionError =
    generateCounterExamplesMutation.error
    || updateCounterExampleCaseMutation.error
    || runCounterExamplesMutation.error
    || finalizeReviewMutation.error
    || reopenReviewMutation.error
  const reviewActionPending =
    generateCounterExamplesMutation.isPending
    || updateCounterExampleCaseMutation.isPending
    || runCounterExamplesMutation.isPending
    || finalizeReviewMutation.isPending
    || reopenReviewMutation.isPending

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ alignItems: { md: 'center' }, justifyContent: 'space-between' }}>
        <Stack spacing={0.5}>
          <Typography component="h1" variant="h1">
            Combination review workspace
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Review relation semantics, approve diagnostic counter-example cases, run evidence, and finalize the human decision.
          </Typography>
        </Stack>
        <Button href={`/runs/${encodedRunName}/constraints?constraintTab=combination&constraintsView=table&combinationId=${encodeURIComponent(combinationId)}`} startIcon={<ArrowBackIcon />} variant="outlined">
          Back to combination table
        </Button>
      </Stack>

      <PageLearningPanel
        sections={[
          {
            body: 'Start by reading relation, status, and runtime support before choosing the next review action.',
            title: 'Understand the row',
          },
          {
            body: 'Generate drafts only when the row needs review, then edit executable JSON before approval.',
            title: 'Approve safe drafts',
          },
          {
            body: 'Run approved cases against an explicit target and finalize the decision with rationale.',
            title: 'Finalize intentionally',
          },
        ]}
      />
      <QueryState
        empty={false}
        error={detailQuery.error ?? reviewQuery.error}
        isError={detailQuery.isError || reviewQuery.isError}
        isLoading={detailQuery.isLoading || reviewQuery.isLoading}
        onRetry={() => {
          void detailQuery.refetch()
          void reviewQuery.refetch()
        }}
      >
        {detailQuery.data ? (
          <Stack spacing={2}>
            <CombinationHitlActivationPanel
              detail={detailQuery.data}
              review={reviewQuery.data}
              route="review_workspace"
              runName={runName}
            />
            <CombinationDetailComposer
              detail={detailQuery.data}
              detailView={detailView}
              evidenceLinks={evidenceLinks}
              mode="workspace"
              onApproveCase={(caseId, request) => handleUpdateCounterExampleCase(caseId, 'APPROVED', 'Approved for targeted HITL execution.', request)}
              onDetailViewChange={setDetailView}
              onFinalize={handleFinalizeReview}
              onGenerateDraft={handleGenerateCounterExamples}
              onRejectCase={(caseId) => handleUpdateCounterExampleCase(caseId, 'REJECTED', 'Rejected during HITL review.')}
              onReopen={handleReopenReview}
              onRunApproved={handleRunApprovedCounterExamples}
              review={reviewQuery.data}
              reviewActionError={reviewActionError}
              reviewActionPending={reviewActionPending}
              reviewLoading={reviewQuery.isLoading}
            />
          </Stack>
        ) : null}
      </QueryState>
    </Stack>
  )
}
