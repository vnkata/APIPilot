import { Button, Card, CardContent, Chip, Grid, MenuItem, Stack, TextField, Typography } from '@mui/material'

import type {
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
} from '../../../shared/api/generated/model'
import { StatusSignalStrip } from '../../../shared/ui/StatusSignalStrip'
import type { MatrixBy } from '../constraintViewModels'
import { parseAssertionSummary } from '../constraintViewModels'
import { CurrentPageConstraintMatrix } from './CurrentPageConstraintMatrix'

type ConstraintWorkbenchProps = {
  constraints: ConstraintExplorerEntryResponse[]
  invariants: InvariantExplorerEntryResponse[]
  matrixBy: MatrixBy
  onApplyFilter: (filter: Record<string, string | undefined>) => void
  onMatrixByChange: (matrixBy: MatrixBy) => void
  onSelectConstraint: (constraintId: string) => void
  onSelectInvariant: (invariantId: string) => void
}

function ConstraintCard({
  constraint,
  onSelect,
}: {
  constraint: ConstraintExplorerEntryResponse
  onSelect: (constraintId: string) => void
}) {
  const assertion = parseAssertionSummary(constraint.assertion_preview)
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Stack spacing={1.25}>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
            <Chip label={constraint.source} size="small" />
            <Chip label={constraint.constraint_kind} size="small" variant="outlined" />
            <Chip label={constraint.agreement_status} size="small" variant="outlined" />
          </Stack>
          <Button color="inherit" onClick={() => onSelect(constraint.constraint_id)} size="small" sx={{ justifyContent: 'flex-start', p: 0, textAlign: 'left' }}>
            {constraint.expression}
          </Button>
          <Typography color="text.secondary" variant="body2">
            {constraint.operation_id} · {constraint.property_path}
          </Typography>
          <Chip label={assertion.title} size="small" sx={{ alignSelf: 'flex-start' }} variant="outlined" />
        </Stack>
      </CardContent>
    </Card>
  )
}

function InvariantCard({
  invariant,
  onSelect,
}: {
  invariant: InvariantExplorerEntryResponse
  onSelect: (invariantId: string) => void
}) {
  const assertion = parseAssertionSummary(invariant.assertion_preview)
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Stack spacing={1.25}>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
            <Chip label={invariant.invariant_kind} size="small" />
            <Chip label={invariant.oracle_readiness} size="small" variant="outlined" />
            <Chip label={invariant.correlation_confidence} size="small" variant="outlined" />
          </Stack>
          <Button color="inherit" onClick={() => onSelect(invariant.invariant_id)} size="small" sx={{ justifyContent: 'flex-start', p: 0, textAlign: 'left' }}>
            {invariant.invariant ?? invariant.invariant_id}
          </Button>
          <Typography color="text.secondary" variant="body2">
            {invariant.operation_id ?? 'No operation'} · {invariant.primary_property_path ?? 'No property path'}
          </Typography>
          <Chip label={assertion.title} size="small" sx={{ alignSelf: 'flex-start' }} variant="outlined" />
        </Stack>
      </CardContent>
    </Card>
  )
}

export function ConstraintWorkbench({
  constraints,
  invariants,
  matrixBy,
  onApplyFilter,
  onMatrixByChange,
  onSelectConstraint,
  onSelectInvariant,
}: ConstraintWorkbenchProps) {
  const assertionAvailable = constraints.filter((row) => row.assertion_available).length + invariants.filter((row) => row.assertion_available).length
  const bothPresent = constraints.filter((row) => row.agreement_status === 'both_present').length
  const readyInvariants = invariants.filter((row) => row.oracle_readiness === 'verified_runtime_oracle' || row.oracle_readiness === 'schema_supported').length

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' } }}>
        <Stack spacing={0.5} sx={{ flex: 1 }}>
          <Typography component="h2" variant="h2">
            Constraint Workbench
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Triage readable constraints, source lineage, assertion coverage, and invariant evidence without opening raw JSON.
          </Typography>
        </Stack>
        <StatusSignalStrip
          ariaLabel="Constraint workbench signals"
          signals={[
            { label: 'Current page constraints', value: constraints.length },
            { label: 'Current page invariants', value: invariants.length },
            { label: 'Both present', tone: bothPresent > 0 ? 'success' : 'neutral', value: bothPresent },
            { label: 'Assertions', tone: assertionAvailable > 0 ? 'success' : 'neutral', value: assertionAvailable },
            { label: 'Ready invariants', tone: readyInvariants > 0 ? 'success' : 'neutral', value: readyInvariants },
          ]}
        />
      </Stack>

      <TextField
        label="Matrix"
        onChange={(event) => onMatrixByChange(event.target.value as MatrixBy)}
        select
        size="small"
        sx={{ maxWidth: 240 }}
        value={matrixBy}
      >
        <MenuItem value="source">Source</MenuItem>
        <MenuItem value="kind">Kind</MenuItem>
        <MenuItem value="readiness">Readiness</MenuItem>
      </TextField>

      <CurrentPageConstraintMatrix
        constraints={constraints}
        invariants={invariants}
        matrixBy={matrixBy}
        onApplyFilter={onApplyFilter}
      />

      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Constraint signals
        </Typography>
        <Grid container spacing={2}>
          {constraints.map((constraint) => (
            <Grid key={constraint.constraint_id} size={{ xs: 12, md: 6 }}>
              <ConstraintCard constraint={constraint} onSelect={onSelectConstraint} />
            </Grid>
          ))}
        </Grid>
      </Stack>

      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Invariant evidence
        </Typography>
        <Grid container spacing={2}>
          {invariants.map((invariant) => (
            <Grid key={invariant.invariant_id} size={{ xs: 12, md: 6 }}>
              <InvariantCard invariant={invariant} onSelect={onSelectInvariant} />
            </Grid>
          ))}
        </Grid>
      </Stack>
    </Stack>
  )
}
