import { Box, Button, Grid, MenuItem, Stack, TextField, Typography } from '@mui/material'

import type {
  CombinationEntryResponse,
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
} from '../../../shared/api/generated/model'
import { Panel } from '../../../shared/ui/Panel'
import { monoFontFamily } from '../../../theme/typography'
import { TOUR_ANCHORS, tourAnchor } from '../../product-tour/tourAnchors'
import type { MatrixBy } from '../constraintViewModels'
import { deriveCombinationReviewSignal, parseAssertionSummary, readableIdentifier } from '../constraintViewModels'
import {
  AgreementBadge,
  AssertionBadge,
  ConstraintKindBadge,
  ConstraintSourceBadge,
  CorrelationBadge,
  OracleReadinessBadge,
} from './ConstraintBadges'
import {
  CombinationPriorityBadge,
  CombinationRelationBadge,
  CombinationStatusBadge,
  ReviewStateBadge,
  RuntimeVerdictBadge,
} from './CombinationBadges'
import { CurrentPageConstraintMatrix } from './CurrentPageConstraintMatrix'

type ConstraintWorkbenchProps = {
  batchGenerateMessage?: string | null
  batchGeneratePending?: boolean
  combinations: CombinationEntryResponse[]
  constraints: ConstraintExplorerEntryResponse[]
  invariants: InvariantExplorerEntryResponse[]
  matrixBy: MatrixBy
  onApplyFilter: (filter: Record<string, string | undefined>) => void
  onBatchGenerateCounterExamples: () => void
  onMatrixByChange: (matrixBy: MatrixBy) => void
  onSelectCombination: (combinationId: string) => void
  onSelectConstraint: (constraintId: string) => void
  onSelectInvariant: (invariantId: string) => void
}

function SummaryMetric({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <Stack spacing={0.25}>
      <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
        {label}
      </Typography>
      <Typography component="span" sx={{ fontVariantNumeric: 'tabular-nums' }} variant="h3">
        {value}
      </Typography>
    </Stack>
  )
}

function StartHereStrip() {
  const steps = [
    { label: 'Find', text: 'Search or filter by operation/source.' },
    { label: 'Prioritize', text: 'Use readiness and agreement signals.' },
    { label: 'Inspect', text: 'Open detail for full expression evidence.' },
  ]

  return (
    <Box
      aria-label="Constraint workbench start here"
      sx={(theme) => ({
        border: '1px solid',
        borderColor: theme.apiTesting.border.subtle,
        borderRadius: 1.25,
        p: 1,
      })}
    >
      <Grid container spacing={1}>
        {steps.map((step) => (
          <Grid key={step.label} size={{ xs: 12, sm: 4 }}>
            <Stack spacing={0.25}>
              <Typography color="primary.main" sx={{ fontWeight: 900 }} variant="caption">
                {step.label}
              </Typography>
              <Typography color="text.secondary" variant="caption">
                {step.text}
              </Typography>
            </Stack>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

function ConstraintSignalRow({
  constraint,
  onSelect,
}: {
  constraint: ConstraintExplorerEntryResponse
  onSelect: (constraintId: string) => void
}) {
  const assertion = parseAssertionSummary(constraint.assertion_preview)

  return (
    <Box
      sx={(theme) => ({
        border: '1px solid',
        borderColor: theme.apiTesting.border.default,
        borderRadius: 1.25,
        p: 1.25,
      })}
    >
      <Stack spacing={1}>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
          <ConstraintSourceBadge source={constraint.source} />
          <AgreementBadge agreement={constraint.agreement_status} />
          <AssertionBadge available={constraint.assertion_available} />
        </Stack>
        <Typography
          component="p"
          sx={{
            display: '-webkit-box',
            fontFamily: monoFontFamily,
            overflow: 'hidden',
            overflowWrap: 'anywhere',
            WebkitBoxOrient: 'vertical',
            WebkitLineClamp: 2,
          }}
          variant="body2"
        >
          {constraint.expression}
        </Typography>
        <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
          <ConstraintKindBadge kind={constraint.constraint_kind} />
          <Typography
            color="text.secondary"
            sx={{ flex: 1, minWidth: 180, overflowWrap: 'anywhere' }}
            variant="caption"
          >
            {readableIdentifier(constraint.operation_id)} / {readableIdentifier(constraint.property_path)}
          </Typography>
          <Button onClick={() => onSelect(constraint.constraint_id)} size="small" variant="outlined">
            Open detail
          </Button>
        </Stack>
        <Typography color="text.secondary" variant="caption">
          Assertion: {assertion.title}
        </Typography>
      </Stack>
    </Box>
  )
}

function InvariantSignalRow({
  invariant,
  onSelect,
}: {
  invariant: InvariantExplorerEntryResponse
  onSelect: (invariantId: string) => void
}) {
  const assertion = parseAssertionSummary(invariant.assertion_preview)

  return (
    <Box
      sx={(theme) => ({
        border: '1px solid',
        borderColor: theme.apiTesting.border.default,
        borderRadius: 1.25,
        p: 1.25,
      })}
    >
      <Stack spacing={1}>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
          <OracleReadinessBadge readiness={invariant.oracle_readiness} />
          <CorrelationBadge confidence={invariant.correlation_confidence} />
          <AssertionBadge available={invariant.assertion_available} />
        </Stack>
        <Typography
          component="p"
          sx={{
            display: '-webkit-box',
            fontFamily: monoFontFamily,
            overflow: 'hidden',
            overflowWrap: 'anywhere',
            WebkitBoxOrient: 'vertical',
            WebkitLineClamp: 2,
          }}
          variant="body2"
        >
          {invariant.invariant ?? invariant.invariant_id}
        </Typography>
        <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
          <Typography
            color="text.secondary"
            sx={{ flex: 1, minWidth: 180, overflowWrap: 'anywhere' }}
            variant="caption"
          >
            {readableIdentifier(invariant.operation_id)} / {readableIdentifier(invariant.primary_property_path)}
          </Typography>
          <Button onClick={() => onSelect(invariant.invariant_id)} size="small" variant="outlined">
            Open detail
          </Button>
        </Stack>
        <Typography color="text.secondary" variant="caption">
          Assertion: {assertion.title}
        </Typography>
      </Stack>
    </Box>
  )
}

function CombinationSignalRow({
  combination,
  onSelect,
}: {
  combination: CombinationEntryResponse
  onSelect: (combinationId: string) => void
}) {
  return (
    <Box
      sx={(theme) => ({
        border: '1px solid',
        borderColor: theme.apiTesting.border.default,
        borderRadius: 1.25,
        p: 1.25,
      })}
    >
      <Stack spacing={1}>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
          <CombinationPriorityBadge row={combination} />
          <CombinationRelationBadge relation={combination.relation} />
          <CombinationStatusBadge status={combination.status} />
          <RuntimeVerdictBadge runtimeVerdict={combination.runtime_verdict} />
          <ReviewStateBadge row={combination} />
        </Stack>
        <Typography
          component="p"
          sx={{
            display: '-webkit-box',
            fontFamily: monoFontFamily,
            overflow: 'hidden',
            overflowWrap: 'anywhere',
            WebkitBoxOrient: 'vertical',
            WebkitLineClamp: 2,
          }}
          variant="body2"
        >
          {combination.final_constraint ?? combination.static_constraint ?? combination.dynamic_constraint ?? combination.combination_id}
        </Typography>
        <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 0.75 }}>
          <Typography
            color="text.secondary"
            sx={{ flex: 1, minWidth: 180, overflowWrap: 'anywhere' }}
            variant="caption"
          >
            {readableIdentifier(combination.operation_id)} / {readableIdentifier(combination.property_path)}
          </Typography>
          <Button onClick={() => onSelect(combination.combination_id)} size="small" variant="outlined">
            Open detail
          </Button>
        </Stack>
        <Typography color="text.secondary" variant="caption">
          Evidence: runtime {combination.has_runtime_evaluation ? 'available' : 'missing'}, validation cases {combination.validation_case_count}
        </Typography>
      </Stack>
    </Box>
  )
}

function constraintRank(row: ConstraintExplorerEntryResponse) {
  return (
    (row.assertion_available ? 100 : 0) +
    (row.agreement_status === 'both_present' ? 40 : 0) +
    (row.source === 'combined' ? 20 : row.source === 'dynamic' ? 10 : 0)
  )
}

function invariantRank(row: InvariantExplorerEntryResponse) {
  return (
    (row.assertion_available ? 100 : 0) +
    (row.oracle_readiness === 'verified_runtime_oracle' ? 40 : 0) +
    (row.correlation_confidence === 'exact' ? 20 : row.correlation_confidence === 'derived' ? 10 : 0)
  )
}

function combinationRank(row: CombinationEntryResponse) {
  const priority = deriveCombinationReviewSignal(row).priority
  if (priority === 'conflict') return 500
  if (priority === 'needs_review') return 400
  if (priority === 'human_decision') return 300
  if (priority === 'unique') return 200
  if (priority === 'resolved') return 100
  return 0
}

export function ConstraintWorkbench({
  batchGenerateMessage,
  batchGeneratePending = false,
  combinations,
  constraints,
  invariants,
  matrixBy,
  onApplyFilter,
  onBatchGenerateCounterExamples,
  onMatrixByChange,
  onSelectCombination,
  onSelectConstraint,
  onSelectInvariant,
}: ConstraintWorkbenchProps) {
  const assertionAvailable = constraints.filter((row) => row.assertion_available).length + invariants.filter((row) => row.assertion_available).length
  const bothPresent = constraints.filter((row) => row.agreement_status === 'both_present').length
  const resolvedCombinations = combinations.filter((row) => row.resolved).length
  const readyInvariants = invariants.filter((row) => row.oracle_readiness === 'verified_runtime_oracle' || row.oracle_readiness === 'schema_supported').length
  const topConstraints = [...constraints].sort((left, right) => constraintRank(right) - constraintRank(left)).slice(0, 5)
  const topCombinations = [...combinations]
    .sort((left, right) => combinationRank(right) - combinationRank(left) || right.validation_case_count - left.validation_case_count)
    .slice(0, 3)
  const topInvariants = [...invariants].sort((left, right) => invariantRank(right) - invariantRank(left)).slice(0, 3)

  return (
    <Stack spacing={2} {...tourAnchor(TOUR_ANCHORS.constraintsWorkbench)}>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Panel
            actions={
              <TextField
                label="Matrix"
                onChange={(event) => onMatrixByChange(event.target.value as MatrixBy)}
                select
                size="small"
                sx={{ minWidth: 180 }}
                value={matrixBy}
              >
                <MenuItem value="source">Source</MenuItem>
                <MenuItem value="kind">Kind</MenuItem>
                <MenuItem value="readiness">Readiness</MenuItem>
              </TextField>
            }
            subtitle="Current-page constraint signals and raw Daikon rows for fast triage before opening raw detail."
            title="Constraint Workbench"
          >
            <Stack spacing={1.25}>
              <StartHereStrip />
              <Grid container spacing={1.25}>
                <Grid size={{ xs: 6 }}>
                  <SummaryMetric label="Mapped constraints" value={constraints.length} />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <SummaryMetric label="Raw invariants" value={invariants.length} />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <SummaryMetric label="Combination" value={combinations.length} />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <SummaryMetric label="Resolved" value={resolvedCombinations} />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <SummaryMetric label="Both present" value={bothPresent} />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <SummaryMetric label="Ready oracles" value={readyInvariants} />
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <Typography color="text.secondary" variant="body2">
                    {assertionAvailable} current-page signals have executable assertion evidence.
                  </Typography>
                </Grid>
              </Grid>
            </Stack>
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <CurrentPageConstraintMatrix
            compact
            constraints={constraints}
            invariants={invariants}
            matrixBy={matrixBy}
            onApplyFilter={onApplyFilter}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Panel
            subtitle="Curated from the current page. Open a row for full expression comparison and raw fields."
            title="Top constraint signals"
          >
            <Stack spacing={1}>
              {topConstraints.length > 0 ? (
                topConstraints.map((constraint) => (
                  <ConstraintSignalRow
                    constraint={constraint}
                    key={constraint.constraint_id}
                    onSelect={onSelectConstraint}
                  />
                ))
              ) : (
                <Typography color="text.secondary" variant="body2">
                  No current-page constraint signals match the active filters.
                </Typography>
              )}
            </Stack>
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Panel
            actions={
              <Button
                disabled={combinations.length === 0 || batchGeneratePending}
                onClick={onBatchGenerateCounterExamples}
                size="small"
                variant="outlined"
              >
                Batch generate drafts
              </Button>
            }
            subtitle="Prioritized static/dynamic combinations that need review, conflict resolution, or final inspection."
            title="Combination evidence"
          >
            <Stack spacing={1}>
              {batchGenerateMessage ? (
                <Typography color="text.secondary" variant="body2">
                  {batchGenerateMessage}
                </Typography>
              ) : null}
              {topCombinations.length > 0 ? (
                topCombinations.map((combination) => (
                  <CombinationSignalRow
                    combination={combination}
                    key={combination.combination_id}
                    onSelect={onSelectCombination}
                  />
                ))
              ) : (
                <Typography color="text.secondary" variant="body2">
                  No combination evidence is available for the current filters.
                </Typography>
              )}
            </Stack>
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Panel
            subtitle="Raw Daikon rows that explain mapped dynamic constraints and oracle readiness."
            title="Raw invariant evidence"
          >
            <Stack spacing={1}>
              {topInvariants.length > 0 ? (
                topInvariants.map((invariant) => (
                  <InvariantSignalRow
                    invariant={invariant}
                    key={invariant.invariant_id}
                    onSelect={onSelectInvariant}
                  />
                ))
              ) : (
                <Typography color="text.secondary" variant="body2">
                  No raw invariant evidence is available for the current filters.
                </Typography>
              )}
            </Stack>
          </Panel>
        </Grid>
      </Grid>
    </Stack>
  )
}
