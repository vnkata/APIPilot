import DownloadIcon from '@mui/icons-material/Download'
import { Button, Stack, Typography } from '@mui/material'

import { PageHeader } from '../../../shared/ui/PageHeader'
import { Panel } from '../../../shared/ui/Panel'
import { TOUR_ANCHORS, tourAnchor } from '../../product-tour/tourAnchors'
import type { ConstraintTab } from '../ConstraintsPage'
import { ConstraintModeSegments } from './ConstraintModeSegments'

type ConstraintPageHeaderProps = {
  constraintTab: ConstraintTab
  constraintsView: 'matrix' | 'table' | 'workbench'
  dynamicCount: number
  invariantCount: number
  onExport: () => void
  staticCount: number
}

function MetricBlock({
  label,
  value,
}: {
  label: string
  value: number
}) {
  return (
    <Stack role="listitem" spacing={0.25} sx={{ minWidth: 104 }}>
      <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
        {label}
      </Typography>
      <Typography component="span" sx={{ fontVariantNumeric: 'tabular-nums' }} variant="h3">
        {value}
      </Typography>
    </Stack>
  )
}

export function ConstraintPageHeader({
  constraintTab,
  constraintsView,
  dynamicCount,
  invariantCount,
  onExport,
  staticCount,
}: ConstraintPageHeaderProps) {
  return (
    <Stack spacing={1.5}>
      <PageHeader
        actions={
          <Stack
            direction="row"
            spacing={1}
            sx={{ flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}
          >
            <ConstraintModeSegments constraintTab={constraintTab} constraintsView={constraintsView} />
            <Button onClick={onExport} startIcon={<DownloadIcon />} variant="outlined">
              Export snapshot
            </Button>
          </Stack>
        }
        eyebrow="Constraint oracle workspace"
        subtitle="Triage generated constraints, invariant candidates, and assertion readiness from cached run artifacts."
        title="Constraints and invariants"
        {...tourAnchor(TOUR_ANCHORS.constraintsHeader)}
      />
      <Panel aria-label="Constraint workspace summary" sx={{ p: 1.5 }}>
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          role="list"
          spacing={2}
          sx={{ alignItems: { sm: 'center' }, justifyContent: 'space-between' }}
        >
          <MetricBlock label="Static" value={staticCount} />
          <MetricBlock label="Dynamic" value={dynamicCount} />
          <MetricBlock label="Invariants" value={invariantCount} />
        </Stack>
      </Panel>
    </Stack>
  )
}
