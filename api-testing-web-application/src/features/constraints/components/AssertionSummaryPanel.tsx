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

import { JsonBlock } from '../../../shared/ui/JsonBlock'
import { parseAssertionSummary } from '../constraintViewModels'

type AssertionSummaryPanelProps = {
  assertion?: string | null
}

export function AssertionSummaryPanel({ assertion }: AssertionSummaryPanelProps) {
  const summary = parseAssertionSummary(assertion)
  const showCode = Boolean(summary.code)

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.25}>
          <Stack direction="row" sx={{ alignItems: 'flex-start', gap: 1, justifyContent: 'space-between' }}>
            <Stack spacing={0.5} sx={{ minWidth: 0 }}>
              <Typography component="h3" variant="h3">
                Assertion summary
              </Typography>
              <Typography color="text.secondary" variant="body2">
                {summary.description}
              </Typography>
            </Stack>
            <Chip label={summary.title} size="small" />
          </Stack>
          {summary.subject ? (
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
              <Chip label={`Subject: ${summary.subject}`} size="small" variant="outlined" />
              {summary.expectation ? <Chip label={`Expectation: ${summary.expectation}`} size="small" variant="outlined" /> : null}
            </Stack>
          ) : null}
          {showCode ? (
            <Accordion disableGutters slotProps={{ transition: { unmountOnExit: true } }} variant="outlined">
              <AccordionSummary expandIcon={<ExpandMoreIcon fontSize="small" />}>
                <Typography component="span" variant="subtitle2">Assertion code</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <JsonBlock ariaLabel="assertion code" maxHeight={180} value={summary.code} />
              </AccordionDetails>
            </Accordion>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  )
}
