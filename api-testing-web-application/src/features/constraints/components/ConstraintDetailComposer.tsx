import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Card,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from '@mui/material'

import type { ConstraintExplorerDetailResponse } from '../../../shared/api/generated/model'
import { monoFontFamily } from '../../../theme/typography'
import { EvidenceLinkSet } from '../../../shared/ui/EvidenceLinkSet'
import { JsonBlock } from '../../../shared/ui/JsonBlock'
import { ViewModeToggle } from '../../../shared/ui/ViewModeToggle'
import { deriveConstraintLineage, readableIdentifier } from '../constraintViewModels'
import { AssertionSummaryPanel } from './AssertionSummaryPanel'
import {
  AgreementBadge,
  AssertionBadge,
  ConstraintKindBadge,
  ConstraintSourceBadge,
} from './ConstraintBadges'
import { ConstraintMetadataPanel } from './ConstraintMetadataPanel'
import { ConstraintReadingGuide } from './ConstraintReadingGuide'

type ConstraintDetailComposerProps = {
  detail: ConstraintExplorerDetailResponse
  detailView: 'raw' | 'readable'
  evidenceLinks: Array<{ href: string; label: string }>
  onDetailViewChange: (value: 'raw' | 'readable') => void
}

function ExpressionCard({
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

export function ConstraintDetailComposer({
  detail,
  detailView,
  evidenceLinks,
  onDetailViewChange,
}: ConstraintDetailComposerProps) {
  const lineage = deriveConstraintLineage(detail)

  if (detailView === 'raw') {
    return (
      <Stack spacing={2}>
        <ViewModeToggle
          ariaLabel="Constraint detail view"
          onChange={onDetailViewChange}
          options={[
            { label: 'Readable', value: 'readable' },
            { label: 'Raw', value: 'raw' },
          ]}
          value={detailView}
        />
        <JsonBlock ariaLabel="constraint raw fields" value={detail} />
      </Stack>
    )
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'flex-end' }}>
        <ViewModeToggle
          ariaLabel="Constraint detail view"
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
            <ConstraintSourceBadge source={detail.source} />
            <ConstraintKindBadge kind={detail.constraint_kind} />
            <AgreementBadge agreement={detail.agreement_status} />
            <AssertionBadge available={detail.assertion_available} />
          </>
        }
        items={[
          { label: 'Operation', value: readableIdentifier(detail.operation_id) },
          { label: 'Property', value: readableIdentifier(detail.property_path) },
          { label: 'Section', value: readableIdentifier(detail.section) },
          { label: 'Source type', value: readableIdentifier(detail.source_type) },
        ]}
        title="Constraint context"
      />

      <ConstraintReadingGuide kind="constraint" />

      <EvidenceLinkSet links={evidenceLinks} />

      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Source lineage
        </Typography>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
          {lineage.signals.map((signal) => (
            <Chip
              key={signal.label}
              label={signal.label}
              size="small"
              title={signal.description}
              variant={signal.tone === 'success' ? 'filled' : 'outlined'}
            />
          ))}
        </Stack>
        {lineage.textMatches.length > 0 ? (
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            {lineage.textMatches.map((match) => (
              <Chip key={match} label={match} size="small" variant="outlined" />
            ))}
          </Stack>
        ) : (
          <Typography color="text.secondary" variant="body2">
            No exact text match was found across available expressions.
          </Typography>
        )}
      </Stack>

      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Expression comparison
        </Typography>
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12 }}>
            <ExpressionCard label="Static" value={detail.static_expression} />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <ExpressionCard label="Dynamic" value={detail.dynamic_expression} />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <ExpressionCard label="Combined" value={detail.combined_expression ?? detail.expression} />
          </Grid>
        </Grid>
      </Stack>

      <AssertionSummaryPanel assertion={detail.assertion ?? detail.assertion_preview} />

      <Accordion disableGutters slotProps={{ transition: { unmountOnExit: true } }} variant="outlined">
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
          <Typography component="span" variant="subtitle2">Raw fields</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <JsonBlock ariaLabel="constraint raw fields" value={detail} />
        </AccordionDetails>
      </Accordion>
    </Stack>
  )
}
