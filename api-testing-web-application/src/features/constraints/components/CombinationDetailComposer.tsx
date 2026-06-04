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
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
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
  CounterExampleCaseResponse,
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
  CaseRiskBadge,
  CaseStateBadge,
  GenerationBadge,
  RelationGuide,
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

function validateExecutableRequest(value: unknown): string | null {
  const request = asPlainRecord(value)
  if (!request) return 'Request draft must be a JSON object before approval.'
  const method = request.method
  const path = request.path
  if (typeof method !== 'string' || !method.trim()) return 'Request draft must include a non-empty method.'
  if (typeof path !== 'string' || !path.trim()) return 'Request draft must include a non-empty path.'
  if (containsRedactedExecutableValue(value)) {
    return 'Request draft contains redacted executable values. Regenerate or replace them before approval.'
  }
  return null
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

function asPlainRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function requestMethod(request: unknown) {
  const method = asPlainRecord(request)?.method
  return typeof method === 'string' && method.trim() ? method.trim().toUpperCase() : 'UNKNOWN'
}

function requestPath(request: unknown) {
  const path = asPlainRecord(request)?.path
  return typeof path === 'string' && path.trim() ? path.trim() : 'Path unavailable'
}

function requestSection(request: unknown, key: string) {
  return asPlainRecord(request)?.[key] ?? null
}

function isUnsafeHttpMethod(method: string) {
  return !['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase())
}

function methodRiskText(method: string) {
  const normalized = method.toUpperCase()
  if (normalized === 'DELETE') return 'DELETE has the highest mutation risk. Confirm this target is safe before execution.'
  if (isUnsafeHttpMethod(normalized)) return `${normalized} can mutate the target API. Confirm unsafe methods before execution.`
  if (normalized === 'GET') return 'GET is a read-style method and usually low risk.'
  if (normalized === 'HEAD' || normalized === 'OPTIONS') return `${normalized} is a read-style discovery method and usually low risk.`
  return 'Unknown method risk. Review this request before execution.'
}

function hasRuntimeEvidence(review?: CombinationReviewResponse) {
  return Boolean(
    review?.runtime_recommendation && review.runtime_recommendation !== 'NO_RECOMMENDATION',
  ) || Boolean(review?.cases.some((item) => item.runtime_result || item.runtime_verdict))
}

function hasCaseRuntimeEvidence(item: CounterExampleCaseResponse) {
  return Boolean(item.runtime_result || item.runtime_verdict || item.case_state === 'EXECUTED')
}

function validPositiveNumber(value: string) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0
}

function relationRisk(detail: CombinationDetailResponse) {
  if (detail.relation === 'DISJOINT' || detail.status === 'CONFLICT') return 'High: static and dynamic evidence appear incompatible.'
  if (detail.relation === 'DYNAMIC_STRONGER' || detail.relation === 'PARTIAL_OVERLAP' || detail.relation === 'UNKNOWN') {
    return 'Medium: this row needs human review before it should become final.'
  }
  if (detail.status === 'UNIQUE_STATIC' || detail.status === 'UNIQUE_DYNAMIC') return 'Low: only one source produced this constraint.'
  return 'Low: the combiner already has a resolved recommendation.'
}

function relationDescription(relation: string | null | undefined) {
  if (relation === 'EQUIVALENT') return 'Static and dynamic constraints describe the same valid cases.'
  if (relation === 'STATIC_STRONGER') return 'Static constraint is more restrictive than dynamic evidence.'
  if (relation === 'DYNAMIC_STRONGER') return 'Dynamic constraint is more restrictive and needs review before finalization.'
  if (relation === 'PARTIAL_OVERLAP') return 'Static and dynamic constraints overlap but neither fully implies the other.'
  if (relation === 'DISJOINT') return 'Static and dynamic constraints appear incompatible.'
  if (relation === 'UNKNOWN') return 'The relation cannot be determined from available context.'
  return 'Unique rows have only one available constraint side.'
}

function RelationSummaryPanel({
  detail,
  review,
}: {
  detail: CombinationDetailResponse
  review?: CombinationReviewResponse
}) {
  const signal = deriveCombinationReviewSignal(detail)
  const semanticRows = [
    { label: 'Meaning', value: relationDescription(detail.relation) },
    { label: 'Risk', value: relationRisk(detail) },
    { label: 'Recommended next action', value: signal.recommendedNextAction },
    { label: 'Raw enum', value: detail.relation ?? detail.status ?? 'null' },
  ]

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
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
            {signal.description}
          </Typography>
          <Box aria-label="Relation semantics" role="region">
            <Typography component="h3" variant="h3">
              Relation semantics
            </Typography>
            <Grid container spacing={1} sx={{ mt: 0.25 }}>
              {semanticRows.map((row) => (
                <Grid key={row.label} size={{ xs: 12, md: 6 }}>
                  <Stack
                    spacing={0.25}
                    sx={(theme) => ({
                      border: '1px solid',
                      borderColor: theme.apiTesting.border.default,
                      borderRadius: 1,
                      height: '100%',
                      p: 1,
                    })}
                  >
                    <Typography color="text.secondary" variant="caption">
                      {row.label}
                    </Typography>
                    <Typography variant="body2">
                      {row.value}
                    </Typography>
                  </Stack>
                </Grid>
              ))}
            </Grid>
          </Box>
          <RelationGuide />
        </Stack>
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
      const validationError = validateExecutableRequest(request)
      if (validationError) {
        setDraftRequestErrors((current) => ({
          ...current,
          [caseId]: validationError,
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
                    <CaseStateBadge state={item.case_state} />
                    {item.risk ? <CaseRiskBadge risk={item.risk} /> : null}
                    {item.generation_id ? <GenerationBadge generationId={item.generation_id} /> : null}
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

function RunEvidencePanel({
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
  const runnableCases = review?.cases.filter((item) => item.case_state === 'APPROVED') ?? []
  const evidenceCases = review?.cases.filter(hasCaseRuntimeEvidence) ?? []
  const runnableCaseCount = runnableCases.length
  const hasUnsafeRunnableCase = runnableCases.some((item) => isUnsafeHttpMethod(requestMethod(item.request)))
  const baseUrlSuggestions = review?.target_base_url_suggestions ?? []
  const runtimeCaseCount = evidenceCases.length
  const runReady =
    runnableCaseCount > 0
    && Boolean(baseUrl.trim())
    && validPositiveNumber(requestBudget)
    && validPositiveNumber(timeoutSeconds)
    && (!hasUnsafeRunnableCase || unsafeMethodConfirmed)

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
            Run evidence readiness
          </Typography>
          <Alert severity="info" variant="outlined">
            Runtime evidence is support, not proof. Use it to inform the manual decision, not to auto-finalize constraints.
          </Alert>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button disabled={pending} onClick={handleGenerateDraft} size="small" variant="outlined">
              Generate draft
            </Button>
            <FormControlLabel
              control={<Checkbox checked={liveLlm} onChange={(event) => setLiveLlm(event.target.checked)} size="small" />}
              label="Use live LLM"
            />
          </Stack>
          {liveLlm ? (
            <Alert severity="warning" variant="outlined">
              Live LLM draft generation can add latency and provider cost. Use deterministic generation when you only need a UI rehearsal.
            </Alert>
          ) : null}

          <Stack aria-label="Runnable cases" role="region" spacing={0.75}>
            <Typography component="h3" variant="h3">
              Runnable cases
            </Typography>
            <Typography color="text.secondary" variant="body2">
              Only approved cases can be executed. Executed cases move to Evidence history and are not rerunnable in this MVP.
            </Typography>
            {runnableCases.length ? (
              runnableCases.map((item) => {
                const method = requestMethod(item.request)
                return (
                  <Accordion key={item.case_id} disableGutters variant="outlined">
                    <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
                      <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
                        <CaseStateBadge state={item.case_state} />
                        <CaseRiskBadge risk={isUnsafeHttpMethod(method) ? `${method} mutable` : `${method} low risk`} />
                        <Typography color="text.secondary" variant="caption">
                          {item.case_id} · {requestPath(item.request)}
                        </Typography>
                        <Typography color="text.secondary" variant="caption">
                          {methodRiskText(method)}
                        </Typography>
                      </Stack>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Stack spacing={1}>
                        <Alert severity={method === 'DELETE' ? 'warning' : isUnsafeHttpMethod(method) ? 'warning' : 'success'} variant="outlined">
                          {methodRiskText(method)}
                        </Alert>
                        <Grid container spacing={1}>
                          <Grid size={{ xs: 12, md: 4 }}>
                            <Typography color="text.secondary" variant="caption">
                              Method and path
                            </Typography>
                            <Typography sx={{ fontFamily: monoFontFamily, overflowWrap: 'anywhere' }} variant="body2">
                              {method} {requestPath(item.request)}
                            </Typography>
                          </Grid>
                          <Grid size={{ xs: 12, md: 4 }}>
                            <Typography color="text.secondary" variant="caption">
                              Expected observation
                            </Typography>
                            <Typography color={item.expected_observation ? 'text.primary' : 'text.secondary'} variant="body2">
                              {item.expected_observation ?? 'Not provided'}
                            </Typography>
                          </Grid>
                          <Grid size={{ xs: 12, md: 4 }}>
                            {item.target_truth_vector ? (
                              <JsonBlock ariaLabel={`target truth vector ${item.case_id}`} value={item.target_truth_vector} />
                            ) : (
                              <Typography color="text.secondary" variant="body2">
                                No target truth vector.
                              </Typography>
                            )}
                          </Grid>
                          {requestSection(item.request, 'query') ? (
                            <Grid size={{ xs: 12, md: 6 }}>
                              <JsonBlock ariaLabel={`query preview ${item.case_id}`} value={requestSection(item.request, 'query')} />
                            </Grid>
                          ) : null}
                          {requestSection(item.request, 'body') ? (
                            <Grid size={{ xs: 12, md: 6 }}>
                              <JsonBlock ariaLabel={`body preview ${item.case_id}`} value={requestSection(item.request, 'body')} />
                            </Grid>
                          ) : null}
                        </Grid>
                      </Stack>
                    </AccordionDetails>
                  </Accordion>
                )
              })
            ) : (
              <Typography color="text.secondary" variant="body2">
                No runnable cases are ready. Approve a draft case before running evidence.
              </Typography>
            )}
          </Stack>

          <Stack spacing={0.75}>
            <Typography component="h3" variant="h3">
              HTTP method risk
            </Typography>
            <Alert severity={hasUnsafeRunnableCase ? 'warning' : 'success'} variant="outlined">
              {hasUnsafeRunnableCase
                ? 'One or more approved cases use POST, PUT, PATCH, or DELETE. Confirm unsafe methods before execution.'
                : 'Approved cases use read-style methods or no approved case is selected yet. Unsafe confirmation is not required for GET.'}
            </Alert>
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
            disabled={pending || !runReady}
            onClick={handleRunApproved}
            size="small"
            variant="contained"
          >
            Run approved cases
          </Button>
          <Stack aria-label="Evidence history" role="region" spacing={0.75}>
            <Typography component="h3" variant="h3">
              Evidence history
            </Typography>
            <Alert severity="info" variant="outlined">
              Runtime evidence is support, not proof. Use these observations to inform the manual decision.
            </Alert>
            <Typography color="text.secondary" variant="body2">
              Recommendation: {review?.runtime_recommendation ?? 'NO_RECOMMENDATION'}. Evidence cases recorded: {runtimeCaseCount}.
            </Typography>
            {evidenceCases.length ? (
              evidenceCases.map((item) => (
                <Accordion key={item.case_id} disableGutters variant="outlined">
                  <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
                    <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
                      <CaseStateBadge state={item.case_state} />
                      <RuntimeVerdictBadge runtimeVerdict={item.runtime_verdict} />
                      <Typography color="text.secondary" variant="caption">
                        {item.case_id} · {requestMethod(item.request)} {requestPath(item.request)}
                      </Typography>
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Stack spacing={1}>
                      {item.expected_observation ? (
                        <Alert severity="info" variant="outlined">
                          {item.expected_observation}
                        </Alert>
                      ) : null}
                      {item.runtime_result ? <JsonBlock ariaLabel={`runtime result ${item.case_id}`} value={item.runtime_result} /> : null}
                    </Stack>
                  </AccordionDetails>
                </Accordion>
              ))
            ) : (
              <Typography color="text.secondary" variant="body2">
                No executed evidence has been recorded yet.
              </Typography>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  )
}

const MANUAL_DECISION_OPTIONS = [
  {
    description: 'Use the static constraint as the effective final constraint.',
    label: 'Accept static',
    value: 'ACCEPT_STATIC',
  },
  {
    description: 'Use the dynamic constraint as the effective final constraint.',
    label: 'Accept dynamic',
    value: 'ACCEPT_DYNAMIC',
  },
  {
    description: 'Write a custom final constraint after review.',
    label: 'Custom final',
    value: 'CUSTOM_FINAL',
  },
  {
    description: 'Keep no final combined constraint for this row.',
    label: 'No final',
    value: 'NO_FINAL',
  },
  {
    description: 'Escalate to a domain owner before accepting either side.',
    label: 'Needs business review',
    value: 'NEEDS_BUSINESS_REVIEW',
  },
  {
    description: 'Reject the relation classification and expose no final row.',
    label: 'Reject relation',
    value: 'REJECT_RELATION',
  },
]

function decisionImpact(
  decision: string,
  detail?: CombinationDetailResponse,
  customFinalConstraint?: string,
) {
  if (decision === 'ACCEPT_STATIC') return detail?.static_constraint ?? 'Static constraint will be used when available.'
  if (decision === 'ACCEPT_DYNAMIC') return detail?.dynamic_constraint ?? 'Dynamic constraint will be used when available.'
  if (decision === 'CUSTOM_FINAL') return customFinalConstraint?.trim() || 'A custom final constraint is required.'
  if (decision === 'NO_FINAL') return 'Constraint Explorer overlay will expose no effective combined final for this key.'
  if (decision === 'NEEDS_BUSINESS_REVIEW') return 'The row stays unresolved until business review finishes.'
  if (decision === 'REJECT_RELATION') return 'The relation is rejected and no combined final row should be used for this key.'
  return 'Select a decision to preview the Constraint Explorer impact.'
}

function DecisionSupportPanel({
  detail,
  onFinalize,
  onReopen,
  pending,
  review,
}: {
  detail?: CombinationDetailResponse
  onFinalize: (request: CombinationReviewFinalizeRequest) => void
  onReopen: (rationale: string) => void
  pending?: boolean
  review?: CombinationReviewResponse
}) {
  const [customFinalConstraint, setCustomFinalConstraint] = useState('')
  const [manualDecision, setManualDecision] = useState('')
  const [confirmNoEvidenceOpen, setConfirmNoEvidenceOpen] = useState(false)
  const [rationale, setRationale] = useState('Reviewed by human operator.')
  const [reopenRationale, setReopenRationale] = useState('Reopened for additional review.')
  const runtimeEvidenceAvailable = hasRuntimeEvidence(review)
  const canFinalize = Boolean(
    manualDecision
    && rationale.trim()
    && (manualDecision !== 'CUSTOM_FINAL' || customFinalConstraint.trim()),
  )

  function submitFinalize() {
    onFinalize({
      custom_final_constraint: customFinalConstraint || null,
      idempotency_key: createIdempotencyKey('finalize'),
      manual_decision: manualDecision,
      rationale,
    })
    setConfirmNoEvidenceOpen(false)
  }

  function handleFinalize() {
    if (!canFinalize) return
    if (!runtimeEvidenceAvailable) {
      setConfirmNoEvidenceOpen(true)
      return
    }
    submitFinalize()
  }

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
          <Typography component="h2" variant="h2">
            Final decision support
          </Typography>
          {!runtimeEvidenceAvailable ? (
            <Alert severity="warning" variant="outlined">
              No runtime evidence is attached yet. Finalizing now requires an explicit confirmation and should be treated as a manual judgment.
            </Alert>
          ) : null}
          <Grid container spacing={1}>
            {MANUAL_DECISION_OPTIONS.map((option) => (
              <Grid key={option.value} size={{ xs: 12, md: 4 }}>
                <Button
                  aria-label={option.label}
                  aria-pressed={manualDecision === option.value}
                  color={manualDecision === option.value ? 'primary' : 'inherit'}
                  fullWidth
                  onClick={() => setManualDecision(option.value)}
                  sx={{ alignItems: 'flex-start', justifyContent: 'flex-start', minHeight: 96, textAlign: 'left', whiteSpace: 'normal' }}
                  variant={manualDecision === option.value ? 'contained' : 'outlined'}
                >
                  <Stack spacing={0.5}>
                    <Typography component="span" variant="subtitle2">
                      {option.label}
                    </Typography>
                    <Typography component="span" variant="caption">
                      {option.description}
                    </Typography>
                  </Stack>
                </Button>
              </Grid>
            ))}
          </Grid>
          <TextField fullWidth label="Rationale" onChange={(event) => setRationale(event.target.value)} size="small" value={rationale} />
          {manualDecision === 'CUSTOM_FINAL' ? (
            <Box>
              <TextField fullWidth label="Custom final constraint" onChange={(event) => setCustomFinalConstraint(event.target.value)} size="small" value={customFinalConstraint} />
            </Box>
          ) : null}
          <Alert severity={manualDecision ? 'info' : 'warning'} variant="outlined">
            Impact preview: {decisionImpact(manualDecision, detail, customFinalConstraint)}
          </Alert>
          <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Button disabled={pending || !canFinalize} onClick={handleFinalize} size="small" variant="contained">
              Finalize
            </Button>
            <TextField label="Reopen rationale" onChange={(event) => setReopenRationale(event.target.value)} size="small" sx={{ minWidth: 260 }} value={reopenRationale} />
            <Button disabled={pending} onClick={() => onReopen(reopenRationale)} size="small" variant="outlined">
              Reopen
            </Button>
          </Stack>
        </Stack>
      </CardContent>
      <Dialog
        aria-labelledby="finalize-without-evidence-title"
        onClose={() => setConfirmNoEvidenceOpen(false)}
        open={confirmNoEvidenceOpen}
      >
        <DialogTitle id="finalize-without-evidence-title">Finalize without runtime evidence</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            This row has no executed counter-example evidence yet. Confirm only if the manual decision is intentional and documented by the rationale.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmNoEvidenceOpen(false)}>Cancel</Button>
          <Button onClick={submitFinalize} variant="contained">
            Confirm finalize
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  )
}

function HumanReviewPanel({
  detail,
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
  detail: CombinationDetailResponse
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
      <DraftCaseList onApproveCase={onApproveCase} onRejectCase={onRejectCase} pending={pending} review={review} />
      <RunEvidencePanel onGenerateDraft={onGenerateDraft} onRunApproved={onRunApproved} pending={pending} review={review} />
      <DecisionSupportPanel detail={detail} onFinalize={onFinalize} onReopen={onReopen} pending={pending} review={review} />
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
          detail={detail}
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
