import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { Accordion, AccordionDetails, AccordionSummary, Card, CardContent, Chip, Stack, Typography } from '@mui/material'

import type { ConstraintEntryDetailResponse } from '../../../shared/api/generated/model'
import { JsonBlock } from '../../../shared/ui/JsonBlock'

type LegacyConstraintDetailComposerProps = {
  detail: ConstraintEntryDetailResponse
}

export function LegacyConstraintDetailComposer({ detail }: LegacyConstraintDetailComposerProps) {
  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Chip label={detail.operation_id} size="small" />
        <Chip label={detail.section ?? 'dynamic'} size="small" variant="outlined" />
        <Chip label={detail.property_path} size="small" variant="outlined" />
      </Stack>
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={1}>
            <Typography component="h3" variant="h3">
              Constraint expression
            </Typography>
            <Typography sx={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace', overflowWrap: 'anywhere' }} variant="body2">
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
