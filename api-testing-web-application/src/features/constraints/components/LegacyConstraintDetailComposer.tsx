import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { Accordion, AccordionDetails, AccordionSummary, Card, CardContent, Chip, Stack, Typography } from '@mui/material'

import type { ConstraintEntryDetailResponse } from '../../../shared/api/generated/model'
import { monoFontFamily } from '../../../theme/typography'
import { JsonBlock } from '../../../shared/ui/JsonBlock'
import { readableIdentifier } from '../constraintViewModels'
import { ConstraintMetadataPanel } from './ConstraintMetadataPanel'
import { ConstraintReadingGuide } from './ConstraintReadingGuide'

type LegacyConstraintDetailComposerProps = {
  detail: ConstraintEntryDetailResponse
}

export function LegacyConstraintDetailComposer({ detail }: LegacyConstraintDetailComposerProps) {
  return (
    <Stack spacing={2}>
      <ConstraintMetadataPanel
        badges={<Chip label={detail.section ?? 'dynamic'} size="small" />}
        items={[
          { label: 'Operation', value: readableIdentifier(detail.operation_id) },
          { label: 'Property', value: readableIdentifier(detail.property_path) },
          { label: 'Section', value: readableIdentifier(detail.section) },
        ]}
        title="Legacy constraint context"
      />
      <ConstraintReadingGuide kind="legacy" />
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={1}>
            <Typography component="h3" variant="h3">
              Constraint expression
            </Typography>
            <Typography sx={{ fontFamily: monoFontFamily, overflowWrap: 'anywhere' }} variant="body2">
              {detail.expression}
            </Typography>
          </Stack>
        </CardContent>
      </Card>
      <Accordion disableGutters slotProps={{ transition: { unmountOnExit: true } }} variant="outlined">
        <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
          <Typography component="span" variant="subtitle2">Raw fields</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <JsonBlock ariaLabel="legacy constraint raw fields" value={detail} />
        </AccordionDetails>
      </Accordion>
    </Stack>
  )
}
