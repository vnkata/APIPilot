import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { Accordion, AccordionDetails, AccordionSummary, Stack, Typography } from '@mui/material'

type ConstraintReadingGuideProps = {
  kind: 'constraint' | 'invariant' | 'legacy'
}

const guideCopy = {
  constraint: [
    'Start with the semantic badges to understand source, kind, agreement, and assertion readiness.',
    'Use expression comparison to verify whether static and runtime evidence agree.',
    'Open raw fields only when you need the backend payload shape for debugging.',
  ],
  invariant: [
    'Start with readiness and correlation badges to judge whether the raw Daikon row can become an oracle.',
    'Check assertion summary before trusting the raw invariant as executable test logic.',
    'Use related constraints to connect raw runtime evidence back to mapped or combined constraints.',
  ],
  legacy: [
    'Legacy static/dynamic entries expose the original mined expression for compatibility workflows.',
    'Use operation and property metadata to jump back into explorer filters when needed.',
  ],
}

export function ConstraintReadingGuide({ kind }: ConstraintReadingGuideProps) {
  return (
    <Accordion disableGutters variant="outlined">
      <AccordionSummary expandIcon={<ExpandMoreIcon />} id={`${kind}-reading-guide-header`}>
        <Typography component="span" variant="subtitle2">How to read this</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack component="ul" spacing={0.75} sx={{ m: 0, pl: 2.5 }}>
          {guideCopy[kind].map((item) => (
            <Typography color="text.secondary" component="li" key={item} variant="body2">
              {item}
            </Typography>
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  )
}
