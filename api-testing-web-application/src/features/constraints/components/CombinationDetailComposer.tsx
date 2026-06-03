import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from '@mui/material'
import { useState } from 'react'

import type {
  CombinationDetailResponse,
  CombinationReviewFinalizeRequest,
  CombinationReviewResponse,
  CounterExampleGenerateRequest,
  CounterExampleRunRequest,
  JsonValue,
} from '../../../shared/api/generated/model'
import { EvidenceLinkSet } from '../../../shared/ui/EvidenceLinkSet'
import { JsonBlock } from '../../../shared/ui/JsonBlock'
import { ViewModeToggle } from '../../../shared/ui/ViewModeToggle'
import { monoFontFamily } from '../../../theme/typography'
import {
  deriveCombinationReviewSignal,
  readableIdentifier,
} from '../constraintViewModels'
import {
  CombinationPriorityBadge,
  CombinationRelationBadge,
  CombinationStatusBadge,
  RelationVisual,
  ReviewStateBadge,
  RuntimeVerdictBadge,
} from './CombinationBadges'
import { ConstraintMetadataPanel } from './ConstraintMetadataPanel'
import { CounterExampleRequestEditorLazy } from './CounterExampleRequestEditorLazy'

type CombinationDetailComposerProps = {
  detail: CombinationDetailResponse
  detailView: 'raw' | 'readable'
  evidenceLinks: Array<{ href: string; label: string }>
  mode?: 'preview' | 'workspace'
  onApproveCase: (caseId: string, request: JsonValue | null) => void
  onDetailViewChange: (value: 'raw' | 'readable') => void
  onFinalize: (request: CombinationReviewFinalizeRequest) => void
  onGenerateDraft: (request: CounterExampleGenerateRequest) => void
  onRejectCase: (caseId: string) => void
  onReopen: (rationale: string) => void
  onRunApproved: (request: CounterExampleRunRequest) => void
  review?: CombinationReviewResponse
  reviewActionError?: unknown
  reviewActionPending?: boolean
  reviewHref?: string
  reviewLoading?: boolean
}

function ConstraintCard({
  label,
  value,
}: {
  label: string
  value?: string | null
}) {
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Stack spacing={0.75}>
          <Typography component="h4" variant="subtitle2">
            {label}
          </Typography>
          <Typography
            color={value ? 'text.primary' : 'text.secondary'}
            sx={{ fontFamily: monoFontFamily, overflowWrap: 'anywhere' }}
            variant="body2"
          >
            {value ?? 'Not present'}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}

function EvidenceAccordion({
  label,
  value,
}: {
  label: string
  value: unknown
}) {
  return (
    <Accordion disableGutters slotProps={{ transition: { unmountOnExit: true } }} variant="outlined">
      <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
        <Typography component="span" variant="subtitle2">
          {label}
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <JsonBlock ariaLabel={`${label} evidence`} value={value} />
      </AccordionDetails>
    </Accordion>
  )
}

function createIdempotencyKey(action: string) {
  const randomValue = globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2)
  return `${action}-${Date.now()}-${randomValue}`
}

function containsRedactedExecutableValue(value: unknown): boolean {
  if (value === '<REDACTED>') return true
  if (Array.isArray(value)) return value.some((item) => containsRedactedExecutableValue(item))
  if (value && typeof value === 'object') {
    if ('type' in value && (value as { type?: unknown }).type === 'redacted') return true
    return Object.values(value).some((item) => containsRedactedExecutableValue(item))
  }
  return false
}

function mutationErrorMessage(error: unknown): string | null {
  if (!error) return null
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { error?: { message?: string } } } }).response
    if (response?.data?.error?.message) return response.data.error.message
  }
  if (error instanceof Error) return error.message
  return 'Review action failed.'
}

function reviewStep(review?: CombinationReviewResponse) {
  if (!review) return 0
  if (review.review_state === 'FINAL_CONFIRMED') return 4
  if (review.review_state === 'RUN_COMPLETED') return 3
  if (review.cases.some((item) => item.case_state === 'APPROVED')) return 2
  if (review.cases.length > 0 || review.review_state === 'DRAFT_READY') return 1
  return 0
}

function ReviewProgressRail({ review }: { review?: CombinationReviewResponse }) {
  return (
    <Stepper activeStep={reviewStep(review)} alternativeLabel sx={{ display: { xs: 'none', md: 'flex' } }}>
      {['Understand relation', 'Generate draft', 'Edit and approve draft cases', 'Run evidence', 'Finalize decision'].map((label) => (
        <Step key={label}>
          <StepLabel>{label}</StepLabel>
        </Step>
      ))}
    </Stepper>
  )
}

function RelationSummaryPanel({
  detail,
  review,
}: {
  detail: CombinationDetailResponse
  review?: CombinationReviewResponse
}) {
  const signal = deriveCombinationReviewSignal(detail)

  return (
    <Card variant="outlined">
      <CardContent>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 5 }}>
            <Stack spacing={1}>
              <Typography component="h2" variant="h2">
                Understand relation
              </Typography>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                <CombinationPriorityBadge row={detail} />
                <CombinationRelationBadge relation={detail.relation} />
                <CombinationStatusBadge status={detail.status} />
                <RuntimeVerdictBadge runtimeVerdict={detail.runtime_verdict} />
                <ReviewStateBadge review={review} row={detail} />
              </Stack>
              <Typography color="text.secondary" variant="body2">
                {signal.description} Next action: {signal.recommendedNextAction}
              </Typography>
            </Stack>
          </Grid>
          <Grid size={{ xs: 12, md: 7 }}>
            <RelationVisual relation={detail.relation} />
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )
}

function DraftCaseList({
  onApproveCase,
  onRejectCase,
  pending,
  review,
}: {
  onApproveCase: (caseId: string, request: JsonValue | null) => void
  onRejectCase: (caseId: string) => void
  pending?: boolean
  review?: CombinationReviewResponse
}) {
  const [draftRequestErrors, setDraftRequestErrors] = useState<Record<string, string>>({})
  const [draftRequestText, setDraftRequestText] = useState<Record<string, string>>({})

  function handleApprove(caseId: string, fallbackRequest: unknown) {
    const raw = draftRequestText[caseId] ?? JSON.stringify(fallbackRequest, null, 2)
    try {
      const request = JSON.parse(raw) as JsonValue | null
      if (containsRedactedExecutableValue(request)) {
        setDraftRequestErrors((current) => ({
          ...current,
          [caseId]: 'Request draft contains redacted executable values. Regenerate or replace them before approval.',
        }))
        return
      }
      setDraftRequestErrors((current) => ({ ...current, [caseId]: '' }))
      onApproveCase(caseId, request)
    } catch {
      setDraftRequestErrors((current) => ({
        ...current,
        [caseId]: 'Request draft must be valid JSON before approval.',
      }))
    }
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
          <Typography component="h2" variant="h2">
            Draft cases
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Edit and approve draft cases before execution. The executable request must not contain redacted placeholders.
          </Typography>
          {review?.cases.length ? (
            review.cases.map((item) => (
              <Accordion key={item.case_id} defaultExpanded disableGutters variant="outlined">
                <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
                  <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
                    <ReviewCaseBadge state={item.case_state} />
                    {item.risk ? <ReviewCaseBadge state={`Risk: ${item.risk}`} /> : null}
                    {item.generation_id ? <ReviewCaseBadge state={item.generation_id} /> : null}
                    <Typography color="text.secondary" variant="caption">
                      {item.case_id}
                    </Typography>
                  </Stack>
                </AccordionSummary>
                <AccordionDetails>
                  <Stack spacing={1.25}>
                    <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
                      <Button
                        disabled={pending || item.case_state !== 'DRAFT'}
                        onClick={() => handleApprove(item.case_id, item.request)}
                        size="small"
                        variant="contained"
                      >
                        Approve draft
                      </Button>
                      <Button
                        disabled={pending || item.case_state !== 'DRAFT'}
                        onClick={() => onRejectCase(item.case_id)}
                        size="small"
                        variant="outlined"
                      >
                        Reject draft
                      </Button>
                    </Stack>
                    {item.target_truth_vector ? <EvidenceAccordion label="Target truth vector" value={item.target_truth_vector} /> : null}
                    {item.expected_observation ? (
                      <Alert severity="info" variant="outlined">
                        {item.expected_observation}
                      </Alert>
                    ) : null}
                    {item.validation_error ? <EvidenceAccordion label="Planner validation error" value={item.validation_error} /> : null}
                    {item.request_display ? <EvidenceAccordion label="Redacted request display" value={item.request_display} /> : null}
                    <CounterExampleRequestEditorLazy
                      error={Boolean(draftRequestErrors[item.case_id])}
                      helperText={draftRequestErrors[item.case_id] || 'Edit and approve as valid JSON before execution.'}
                      label={`Request JSON ${item.case_id}`}
                      onChange={(value) => setDraftRequestText((current) => ({ ...current, [item.case_id]: value }))}
                      value={draftRequestText[item.case_id] ?? JSON.stringify(item.request, null, 2)}
                    />
                    {item.runtime_result ? <JsonBlock ariaLabel={`counter-example result ${item.case_id}`} value={item.runtime_result} /> : null}
                  </Stack>
                </AccordionDetails>
              </Accordion>
            ))
          ) : (
            <Typography color="text.secondary" variant="body2">
              No draft counter-example cases have been generated.
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  )
}

function ReviewCaseBadge({ state }: { state: string }) {
  return <ReviewStateBadge row={{ review_state: state } as CombinationDetailResponse} />
}

function ApprovedRunPanel({
  onGenerateDraft,
  onRunApproved,
  pending,
  review,
}: {
  onGenerateDraft: (request: CounterExampleGenerateRequest) => void
  onRunApproved: (request: CounterExampleRunRequest) => void
  pending?: boolean
  review?: CombinationReviewResponse
}) {
  const [baseUrl, setBaseUrl] = useState('')
  const [liveLlm, setLiveLlm] = useState(true)
  const [requestBudget, setRequestBudget] = useState('1')
  const [timeoutSeconds, setTimeoutSeconds] = useState('10')
  const [unsafeMethodConfirmed, setUnsafeMethodConfirmed] = useState(false)
  const approvedCaseCount = review?.cases.filter((item) => item.case_state === 'APPROVED').length ?? 0
  const baseUrlSuggestions = review?.target_base_url_suggestions ?? []

  function handleRunApproved() {
    onRunApproved({
      base_url: baseUrl,
      idempotency_key: createIdempotencyKey('run'),
      live_api: true,
      request_budget: Number(requestBudget),
      timeout_seconds: Number(timeoutSeconds),
      unsafe_method_confirmed: unsafeMethodConfirmed,
    })
  }

  function handleGenerateDraft() {
    onGenerateDraft({
      idempotency_key: createIdempotencyKey('generate'),
      live_llm: liveLlm,
      max_cases: 3,
    })
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
          <Typography component="h2" variant="h2">
            Generate and run evidence
          </Typography>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button disabled={pending} onClick={handleGenerateDraft} size="small" variant="outlined">
              Generate draft
            </Button>
            <FormControlLabel
              control={<Checkbox checked={liveLlm} onChange={(event) => setLiveLlm(event.target.checked)} size="small" />}
              label="Use live LLM"
            />
          </Stack>

          <Grid container spacing={1}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField fullWidth label="Base URL" onChange={(event) => setBaseUrl(event.target.value)} size="small" value={baseUrl} />
              {baseUrlSuggestions.length ? (
                <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75, mt: 0.75 }}>
                  {baseUrlSuggestions.map((url) => (
                    <Button key={url} onClick={() => setBaseUrl(url)} size="small" variant="text">
                      Use {url}
                    </Button>
                  ))}
                </Stack>
              ) : null}
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <TextField
                fullWidth
                label="Request budget"
                onChange={(event) => setRequestBudget(event.target.value)}
                size="small"
                slotProps={{ htmlInput: { min: 1 } }}
                type="number"
                value={requestBudget}
              />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <TextField
                fullWidth
                label="Timeout"
                onChange={(event) => setTimeoutSeconds(event.target.value)}
                size="small"
                slotProps={{ htmlInput: { min: 1 } }}
                type="number"
                value={timeoutSeconds}
              />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <FormControlLabel
                control={<Checkbox checked={unsafeMethodConfirmed} onChange={(event) => setUnsafeMethodConfirmed(event.target.checked)} size="small" />}
                label="Confirm unsafe HTTP methods for this approved run"
              />
            </Grid>
          </Grid>

          <Button
            disabled={pending || approvedCaseCount === 0 || !baseUrl.trim()}
            onClick={handleRunApproved}
            size="small"
            variant="contained"
          >
            Run approved cases
          </Button>
        </Stack>
      </CardContent>
    </Card>
  )
}

function ManualDecisionPanel({
  onFinalize,
  onReopen,
  pending,
}: {
  onFinalize: (request: CombinationReviewFinalizeRequest) => void
  onReopen: (rationale: string) => void
  pending?: boolean
}) {
  const [customFinalConstraint, setCustomFinalConstraint] = useState('')
  const [manualDecision, setManualDecision] = useState('ACCEPT_STATIC')
  const [rationale, setRationale] = useState('Reviewed by human operator.')
  const [reopenRationale, setReopenRationale] = useState('Reopened for additional review.')

  function handleFinalize() {
    onFinalize({
      custom_final_constraint: customFinalConstraint || null,
      idempotency_key: createIdempotencyKey('finalize'),
      manual_decision: manualDecision,
      rationale,
    })
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
          <Typography component="h2" variant="h2">
            Finalize decision
          </Typography>
          <Grid container spacing={1}>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField fullWidth label="Manual decision" onChange={(event) => setManualDecision(event.target.value)} select size="small" value={manualDecision}>
                <MenuItem value="ACCEPT_STATIC">ACCEPT_STATIC</MenuItem>
                <MenuItem value="ACCEPT_DYNAMIC">ACCEPT_DYNAMIC</MenuItem>
                <MenuItem value="CUSTOM_FINAL">CUSTOM_FINAL</MenuItem>
                <MenuItem value="NO_FINAL">NO_FINAL</MenuItem>
                <MenuItem value="NEEDS_BUSINESS_REVIEW">NEEDS_BUSINESS_REVIEW</MenuItem>
                <MenuItem value="REJECT_RELATION">REJECT_RELATION</MenuItem>
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 8 }}>
              <TextField fullWidth label="Rationale" onChange={(event) => setRationale(event.target.value)} size="small" value={rationale} />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth label="Custom final constraint" onChange={(event) => setCustomFinalConstraint(event.target.value)} size="small" value={customFinalConstraint} />
            </Grid>
          </Grid>
          <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Button disabled={pending} onClick={handleFinalize} size="small" variant="contained">
              Finalize
            </Button>
            <TextField label="Reopen rationale" onChange={(event) => setReopenRationale(event.target.value)} size="small" sx={{ minWidth: 260 }} value={reopenRationale} />
            <Button disabled={pending} onClick={() => onReopen(reopenRationale)} size="small" variant="outlined">
              Reopen
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

function HumanReviewPanel({
  onApproveCase,
  onFinalize,
  onGenerateDraft,
  onRejectCase,
  onReopen,
  onRunApproved,
  pending,
  review,
  reviewActionError,
}: {
  onApproveCase: (caseId: string, request: JsonValue | null) => void
  onFinalize: (request: CombinationReviewFinalizeRequest) => void
  onGenerateDraft: (request: CounterExampleGenerateRequest) => void
  onRejectCase: (caseId: string) => void
  onReopen: (rationale: string) => void
  onRunApproved: (request: CounterExampleRunRequest) => void
  pending?: boolean
  review?: CombinationReviewResponse
  reviewActionError?: unknown
}) {
  const actionErrorMessage = mutationErrorMessage(reviewActionError)

  return (
    <Stack aria-label="Human review workflow" role="region" spacing={2}>
      <ReviewProgressRail review={review} />
      {actionErrorMessage ? (
        <Alert severity="error" role="alert">
          {actionErrorMessage}
        </Alert>
      ) : null}
      <ApprovedRunPanel onGenerateDraft={onGenerateDraft} onRunApproved={onRunApproved} pending={pending} review={review} />
      <DraftCaseList onApproveCase={onApproveCase} onRejectCase={onRejectCase} pending={pending} review={review} />
      <ManualDecisionPanel onFinalize={onFinalize} onReopen={onReopen} pending={pending} />
    </Stack>
  )
}

export function CombinationDetailComposer({
  detail,
  detailView,
  evidenceLinks,
  mode = 'workspace',
  onApproveCase,
  onDetailViewChange,
  onFinalize,
  onGenerateDraft,
  onRejectCase,
  onReopen,
  onRunApproved,
  review,
  reviewActionError,
  reviewActionPending,
  reviewHref,
}: CombinationDetailComposerProps) {
  if (detailView === 'raw') {
    return (
      <Stack spacing={2}>
        <ViewModeToggle
          ariaLabel="Combination detail view"
          onChange={onDetailViewChange}
          options={[
            { label: 'Readable', value: 'readable' },
            { label: 'Raw', value: 'raw' },
          ]}
          value={detailView}
        />
        <JsonBlock ariaLabel="combination raw fields" value={detail} />
      </Stack>
    )
  }

  const previewMode = mode === 'preview'

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'flex-end' }}>
        <ViewModeToggle
          ariaLabel="Combination detail view"
          onChange={onDetailViewChange}
          options={[
            { label: 'Readable', value: 'readable' },
            { label: 'Raw', value: 'raw' },
          ]}
          value={detailView}
        />
      </Stack>

      <ConstraintMetadataPanel
        badges={
          <>
            <CombinationPriorityBadge row={detail} />
            <CombinationRelationBadge relation={detail.relation} />
            <CombinationStatusBadge status={detail.status} />
            <RuntimeVerdictBadge runtimeVerdict={detail.runtime_verdict} />
            <ReviewStateBadge review={review} row={detail} />
          </>
        }
        items={[
          { label: 'Operation', value: readableIdentifier(detail.operation_id) },
          { label: 'Property', value: readableIdentifier(detail.property_path) },
          { label: 'Source artifact', value: detail.source_artifact },
          { label: 'Validation cases', value: String(detail.validation_case_count) },
        ]}
        title="Combination context"
      />

      <EvidenceLinkSet links={evidenceLinks} />
      <RelationSummaryPanel detail={detail} review={review} />

      {previewMode ? (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={1}>
              <Typography component="h3" variant="h3">
                Human review preview
              </Typography>
              <Typography color="text.secondary" variant="body2">
                Use the full workspace for draft generation, JSON editing, approved execution, and final decisions.
              </Typography>
              {reviewHref ? (
                <Button href={reviewHref} variant="contained">
                  Open review workspace
                </Button>
              ) : null}
            </Stack>
          </CardContent>
        </Card>
      ) : (
        <HumanReviewPanel
          onApproveCase={onApproveCase}
          onFinalize={onFinalize}
          onGenerateDraft={onGenerateDraft}
          onRejectCase={onRejectCase}
          onReopen={onReopen}
          onRunApproved={onRunApproved}
          pending={reviewActionPending}
          review={review}
          reviewActionError={reviewActionError}
        />
      )}

      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Constraint resolution
        </Typography>
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12, md: 4 }}>
            <ConstraintCard label="Static" value={detail.static_constraint} />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <ConstraintCard label="Dynamic" value={detail.dynamic_constraint} />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <ConstraintCard label="Final" value={detail.final_constraint} />
          </Grid>
        </Grid>
      </Stack>

      {detail.reason ? (
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={0.75}>
              <Typography component="h3" variant="h3">
                Reason
              </Typography>
              <Typography sx={{ overflowWrap: 'anywhere' }} variant="body2">
                {detail.reason}
              </Typography>
            </Stack>
          </CardContent>
        </Card>
      ) : null}

      <Box>
        <EvidenceAccordion label="Runtime evaluation" value={detail.runtime_evaluation ?? { available: false }} />
        <EvidenceAccordion label="Validation cases" value={detail.validation_cases} />
        <EvidenceAccordion label="Counter-example" value={detail.counter_example ?? { available: false }} />
        <EvidenceAccordion label="Sanitized raw record" value={detail.raw_record_sanitized} />
      </Box>
    </Stack>
  )
}
