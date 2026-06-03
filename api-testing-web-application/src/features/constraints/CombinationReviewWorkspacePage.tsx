import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { Button, Stack, Typography } from '@mui/material'
import { useState } from 'react'

import type {
  CombinationReviewFinalizeRequest,
  CounterExampleGenerateRequest,
  CounterExampleRunRequest,
  JsonValue,
} from '../../shared/api/generated/model'
import { encodeRoutePart } from '../../shared/lib/format'
import { PageLearningPanel } from '../../shared/ui/Guidance'
import { QueryState } from '../../shared/ui/QueryState'
import { RelationGuide } from './components/CombinationBadges'
import { CombinationDetailComposer } from './components/CombinationDetailComposer'
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
  const [detailView, setDetailView] = useState<'raw' | 'readable'>('readable')
  const encodedRunName = encodeRoutePart(runName)
  const detailQuery = useCombinationDetail(runName, combinationId)
  const reviewQuery = useCombinationReview(runName, combinationId)

  function refetchReviewSurface() {
    void detailQuery.refetch()
    void reviewQuery.refetch()
  }

  const generateCounterExamplesMutation = useGenerateCounterExamples({
    mutation: { onSuccess: refetchReviewSurface },
  })
  const updateCounterExampleCaseMutation = useUpdateCounterExampleCase({
    mutation: { onSuccess: refetchReviewSurface },
  })
  const runCounterExamplesMutation = useRunCounterExamples({
    mutation: { onSuccess: refetchReviewSurface },
  })
  const finalizeReviewMutation = useFinalizeCombinationReview({
    mutation: { onSuccess: refetchReviewSurface },
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
            body: 'Start by reading relation, status, and runtime support. Runtime evidence is support, not proof.',
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
      <RelationGuide />

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
        ) : null}
      </QueryState>
    </Stack>
  )
}
