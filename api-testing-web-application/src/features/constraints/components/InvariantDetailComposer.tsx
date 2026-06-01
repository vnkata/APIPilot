import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
} from '@mui/material'

import type { InvariantExplorerDetailResponse } from '../../../shared/api/generated/model'
import { monoFontFamily } from '../../../theme/typography'
import { EvidenceLinkSet } from '../../../shared/ui/EvidenceLinkSet'
import { JsonBlock } from '../../../shared/ui/JsonBlock'
import { ViewModeToggle } from '../../../shared/ui/ViewModeToggle'
import { readableIdentifier } from '../constraintViewModels'
import { AssertionSummaryPanel } from './AssertionSummaryPanel'
import {
  AssertionBadge,
  ConstraintKindBadge,
  CorrelationBadge,
  OracleReadinessBadge,
} from './ConstraintBadges'
import { ConstraintMetadataPanel } from './ConstraintMetadataPanel'
import { ConstraintReadingGuide } from './ConstraintReadingGuide'

type InvariantDetailComposerProps = {
  detail: InvariantExplorerDetailResponse
  detailView: 'raw' | 'readable'
  evidenceLinks: Array<{ href: string; label: string }>
  onDetailViewChange: (value: 'raw' | 'readable') => void
}

export function InvariantDetailComposer({
  detail,
  detailView,
  evidenceLinks,
  onDetailViewChange,
}: InvariantDetailComposerProps) {
  if (detailView === 'raw') {
    return (
      <Stack spacing={2}>
        <ViewModeToggle
          ariaLabel="Invariant detail view"
          onChange={onDetailViewChange}
          options={[
            { label: 'Readable', value: 'readable' },
            { label: 'Raw', value: 'raw' },
          ]}
          value={detailView}
        />
        <JsonBlock ariaLabel="invariant raw fields" value={detail} />
      </Stack>
    )
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ justifyContent: 'flex-end' }}>
        <ViewModeToggle
          ariaLabel="Invariant detail view"
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
            <ConstraintKindBadge kind={detail.invariant_kind} />
            <OracleReadinessBadge readiness={detail.oracle_readiness} />
            <CorrelationBadge confidence={detail.correlation_confidence} />
            <AssertionBadge available={detail.assertion_available} />
          </>
        }
        items={[
          { label: 'Operation', value: readableIdentifier(detail.operation_id) },
          { label: 'Primary property', value: readableIdentifier(detail.primary_property_path) },
          { label: 'Raw invariant type', value: readableIdentifier(detail.invariant_type) },
          { label: 'Related mapped constraints', value: detail.related_constraint_ids.length },
        ]}
        title="Raw invariant context"
      />

      <ConstraintReadingGuide kind="invariant" />

      <EvidenceLinkSet links={evidenceLinks} />

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={1}>
            <Typography component="h3" variant="h3">
              Invariant
            </Typography>
            <Typography sx={{ fontFamily: monoFontFamily, overflowWrap: 'anywhere' }} variant="body2">
              {detail.invariant ?? detail.invariant_id}
            </Typography>
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
              {detail.property_paths.map((propertyPath) => (
                <Chip key={propertyPath} label={propertyPath} size="small" variant="outlined" />
              ))}
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      <Stack spacing={1}>
        <Typography component="h3" variant="h3">
          Correlation evidence
        </Typography>
        {detail.correlation_evidence.length > 0 ? (
          detail.correlation_evidence.map((evidence, index) => (
            <Card key={`${evidence.evidence_type}-${index}`} variant="outlined">
              <CardContent>
                <Stack spacing={0.75}>
                  <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                    <Chip label={evidence.evidence_type} size="small" />
                    {evidence.property_path ? <Chip label={evidence.property_path} size="small" variant="outlined" /> : null}
                    {evidence.constraint_id ? <Chip label={evidence.constraint_id} size="small" variant="outlined" /> : null}
                  </Stack>
                  <Typography color="text.secondary" variant="body2">
                    {evidence.message}
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          ))
        ) : (
          <Typography color="text.secondary" variant="body2">
            No correlation evidence is attached to this invariant.
          </Typography>
        )}
      </Stack>

      {detail.related_constraint_ids.length > 0 ? (
        <Stack spacing={1}>
          <Typography component="h3" variant="h3">
            Related constraints
          </Typography>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
            {detail.related_constraint_ids.map((constraintId) => (
              <Chip key={constraintId} label={constraintId} size="small" variant="outlined" />
            ))}
          </Stack>
        </Stack>
      ) : null}

      <AssertionSummaryPanel assertion={detail.postman_assertion ?? detail.assertion_preview} />

      <Accordion disableGutters slotProps={{ transition: { unmountOnExit: true } }} variant="outlined">
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
          <Typography component="span" variant="subtitle2">Raw fields</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <JsonBlock ariaLabel="invariant raw fields" value={detail} />
        </AccordionDetails>
      </Accordion>
    </Stack>
  )
}
