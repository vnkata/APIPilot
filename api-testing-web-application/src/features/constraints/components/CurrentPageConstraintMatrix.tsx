import { ButtonBase, Card, CardContent, Chip, Grid, Stack, Typography } from '@mui/material'

import type {
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
} from '../../../shared/api/generated/model'
import {
  buildCurrentPageConstraintMatrix,
  type MatrixBy,
  type MatrixCell,
} from '../constraintViewModels'

type CurrentPageConstraintMatrixProps = {
  constraints: ConstraintExplorerEntryResponse[]
  invariants: InvariantExplorerEntryResponse[]
  matrixBy: MatrixBy
  onApplyFilter: (filter: Record<string, string | undefined>) => void
}

function MatrixCellCard({ cell, onApplyFilter }: { cell: MatrixCell; onApplyFilter: (filter: Record<string, string | undefined>) => void }) {
  return (
    <ButtonBase
      aria-label={`Filter by ${cell.label}`}
      onClick={() => onApplyFilter(cell.filter)}
      sx={{
        borderRadius: 1,
        display: 'block',
        height: '100%',
        textAlign: 'left',
        width: '100%',
      }}
    >
      <Card variant="outlined" sx={{ height: '100%' }}>
        <CardContent>
          <Stack spacing={0.75}>
            <Typography component="h3" sx={{ overflowWrap: 'anywhere' }} variant="h3">
              {cell.label}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              Current page count
            </Typography>
            <Chip label={cell.count} size="small" sx={{ alignSelf: 'flex-start' }} />
          </Stack>
        </CardContent>
      </Card>
    </ButtonBase>
  )
}

export function CurrentPageConstraintMatrix({
  constraints,
  invariants,
  matrixBy,
  onApplyFilter,
}: CurrentPageConstraintMatrixProps) {
  const matrix = buildCurrentPageConstraintMatrix({ constraints, invariants, matrixBy })
  const agreements = Array.from(new Set(constraints.map((row) => row.agreement_status)))
  const assertionAvailable = constraints.filter((row) => row.assertion_available).length + invariants.filter((row) => row.assertion_available).length

  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography component="h2" variant="h2">
          Readiness matrix
        </Typography>
        <Typography color="text.secondary" variant="body2">
          {matrix.description} Current page only; use filters for full explorer drilldown.
        </Typography>
      </Stack>
      {agreements.length > 0 || assertionAvailable > 0 ? (
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Chip label={`Assertion available (${assertionAvailable})`} size="small" />
          {agreements.map((agreement) => (
            <Chip key={agreement} label={agreement} size="small" variant="outlined" />
          ))}
        </Stack>
      ) : null}
      <Grid container spacing={2}>
        {matrix.cells.length > 0 ? (
          matrix.cells.map((cell) => (
            <Grid key={cell.label} size={{ xs: 12, sm: 6, md: 4 }}>
              <MatrixCellCard cell={cell} onApplyFilter={onApplyFilter} />
            </Grid>
          ))
        ) : (
          <Grid size={{ xs: 12 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography color="text.secondary" variant="body2">
                  No current-page signals are available for this matrix.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Stack>
  )
}
