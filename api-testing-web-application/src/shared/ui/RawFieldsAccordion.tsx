import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Typography,
} from '@mui/material'

import { JsonBlock } from './JsonBlock'

type RawFieldsAccordionProps = {
  maxHeight?: number
  title?: string
  value: unknown
}

export function RawFieldsAccordion({
  maxHeight = 260,
  title = 'Raw fields',
  value,
}: RawFieldsAccordionProps) {
  return (
    <Accordion variant="outlined">
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography component="h4" variant="subtitle2">
          {title}
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <JsonBlock maxHeight={maxHeight} value={value} />
      </AccordionDetails>
    </Accordion>
  )
}
