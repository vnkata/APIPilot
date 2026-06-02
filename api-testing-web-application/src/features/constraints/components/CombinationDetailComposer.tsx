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

import type { CombinationDetailResponse } from '../../../shared/api/generated/model'
import { EvidenceLinkSet } from '../../../shared/ui/EvidenceLinkSet'
import { JsonBlock } from '../../../shared/ui/JsonBlock'
import { ViewModeToggle } from '../../../shared/ui/ViewModeToggle'
import { monoFontFamily } from '../../../theme/typography'
import { readableIdentifier } from '../constraintViewModels'
import { ConstraintMetadataPanel } from './ConstraintMetadataPanel'

type CombinationDetailComposerProps = {
  detail: CombinationDetailResponse
  detailView: 'raw' | 'readable'
  evidenceLinks: Array<{ href: string; label: string }>
  onDetailViewChange: (value: 'raw' | 'readable') => void
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

export function CombinationDetailComposer({
  detail,
  detailView,
  evidenceLinks,
  onDetailViewChange,
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
            {detail.relation ? <Chip label={detail.relation} size="small" variant="outlined" /> : null}
            <Chip label={detail.status} size="small" />
            {detail.runtime_verdict ? <Chip label={detail.runtime_verdict} size="small" variant="outlined" /> : null}
            <Chip
              color={detail.resolved ? 'success' : 'default'}
              label={detail.resolved ? 'Resolved' : 'Unresolved'}
              size="small"
              variant={detail.resolved ? 'filled' : 'outlined'}
            />
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

      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Constraint resolution
        </Typography>
        <Grid container spacing={1.5}>
          <Grid size={{ xs: 12 }}>
            <ConstraintCard label="Static" value={detail.static_constraint} />
          </Grid>
          <Grid size={{ xs: 12 }}>
            <ConstraintCard label="Dynamic" value={detail.dynamic_constraint} />
          </Grid>
          <Grid size={{ xs: 12 }}>
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

      <EvidenceAccordion label="Runtime evaluation" value={detail.runtime_evaluation ?? { available: false }} />
      <EvidenceAccordion label="Validation cases" value={detail.validation_cases} />
      <EvidenceAccordion label="Counter-example" value={detail.counter_example ?? { available: false }} />
      <EvidenceAccordion label="Sanitized raw record" value={detail.raw_record_sanitized} />
    </Stack>
  )
}
