import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined'
import { Box, ButtonBase, Grid, Stack, Tooltip, Typography } from '@mui/material'

import type {
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
} from '../../../shared/api/generated/model'
import { Panel } from '../../../shared/ui/Panel'
import { TOUR_ANCHORS, tourAnchor } from '../../product-tour/tourAnchors'
import {
  buildCurrentPageConstraintMatrix,
  type MatrixBy,
  type MatrixCell,
} from '../constraintViewModels'

type CurrentPageConstraintMatrixProps = {
  compact?: boolean
  constraints: ConstraintExplorerEntryResponse[]
  invariants: InvariantExplorerEntryResponse[]
  matrixBy: MatrixBy
  onApplyFilter: (filter: Record<string, string | undefined>) => void
}

function MatrixCellCard({
  cell,
  compact,
  onApplyFilter,
}: {
  cell: MatrixCell
  compact: boolean
  onApplyFilter: (filter: Record<string, string | undefined>) => void
}) {
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
      <Box
        sx={{
          backgroundColor: (theme) => theme.apiTesting.surface.default,
          border: '1px solid',
          borderColor: (theme) => theme.apiTesting.border.default,
          borderRadius: 1.25,
          boxShadow: 'none',
          height: '100%',
          p: compact ? 1.25 : 1.5,
          transition: (theme) => theme.apiTesting.motion.transition.panel,
          width: '100%',
          '&:hover': {
            borderColor: 'primary.main',
            transform: (theme) => theme.apiTesting.motion.transform.hoverLift,
          },
        }}
      >
        <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
          <Stack spacing={0.25} sx={{ minWidth: 0 }}>
            <Typography
              component="h3"
              sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              variant="subtitle2"
            >
              {cell.label}
            </Typography>
            <Typography color="text.secondary" variant="caption">
              Current page
            </Typography>
          </Stack>
          <Typography component="span" sx={{ fontVariantNumeric: 'tabular-nums' }} variant={compact ? 'h3' : 'h2'}>
            {cell.count}
          </Typography>
        </Stack>
      </Box>
    </ButtonBase>
  )
}

export function CurrentPageConstraintMatrix({
  compact = false,
  constraints,
  invariants,
  matrixBy,
  onApplyFilter,
}: CurrentPageConstraintMatrixProps) {
  const matrix = buildCurrentPageConstraintMatrix({ constraints, invariants, matrixBy })
  const assertionAvailable = constraints.filter((row) => row.assertion_available).length + invariants.filter((row) => row.assertion_available).length

  return (
    <Panel
      subtitle="Click a cell to open a filtered explorer view."
      title={
        <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
          <span>Readiness matrix</span>
          <Tooltip title={`${matrix.description} Counts use only the rows currently loaded for this page.`}>
            <HelpOutlineIcon color="action" fontSize="small" />
          </Tooltip>
        </Stack>
      }
      {...tourAnchor(TOUR_ANCHORS.constraintsMatrix)}
    >
      <Stack spacing={compact ? 1.25 : 2}>
        <Typography color="text.secondary" variant="body2">
          {assertionAvailable} current-page signals include assertion evidence.
        </Typography>
        <Grid container spacing={compact ? 1 : 1.5}>
          {matrix.cells.length > 0 ? (
            matrix.cells.map((cell) => (
              <Grid key={cell.label} size={{ xs: 12, sm: 6, md: compact ? 6 : 4 }}>
                <MatrixCellCard cell={cell} compact={compact} onApplyFilter={onApplyFilter} />
              </Grid>
            ))
          ) : (
            <Grid size={{ xs: 12 }}>
              <Typography color="text.secondary" variant="body2">
                No current-page signals are available for this matrix.
              </Typography>
            </Grid>
          )}
        </Grid>
      </Stack>
    </Panel>
  )
}
