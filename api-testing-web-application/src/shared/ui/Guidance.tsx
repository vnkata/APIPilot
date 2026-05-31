import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined'
import LightbulbOutlinedIcon from '@mui/icons-material/LightbulbOutlined'
import {
  Alert,
  AlertTitle,
  Box,
  ButtonBase,
  Collapse,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { useState, type ReactNode } from 'react'

type InfoHintProps = {
  label: string
  title: ReactNode
}

type DomainTermTooltipProps = {
  definition: ReactNode
  term: ReactNode
}

type GuidanceCalloutProps = {
  bullets?: string[]
  children?: ReactNode
  title: string
}

type PageLearningSection = {
  body: ReactNode
  title: string
}

type PageLearningPanelProps = {
  defaultExpanded?: boolean
  sections: PageLearningSection[]
  title?: string
}

export function InfoHint({ label, title }: InfoHintProps) {
  return (
    <Tooltip describeChild title={title}>
      <IconButton aria-label={label} size="small">
        <HelpOutlineIcon color="action" fontSize="small" />
      </IconButton>
    </Tooltip>
  )
}

export function DomainTermTooltip({ definition, term }: DomainTermTooltipProps) {
  return (
    <Tooltip describeChild title={definition}>
      <Box
        component="span"
        sx={{
          borderBottom: '1px dotted currentColor',
          cursor: 'help',
          fontWeight: 800,
        }}
        tabIndex={0}
      >
        {term}
      </Box>
    </Tooltip>
  )
}

export function GuidanceCallout({ bullets, children, title }: GuidanceCalloutProps) {
  return (
    <Alert icon={<LightbulbOutlinedIcon fontSize="inherit" />} severity="info" variant="outlined">
      <AlertTitle>{title}</AlertTitle>
      {children}
      {bullets?.length ? (
        <Stack component="ul" spacing={0.5} sx={{ m: 0, pl: 2.5 }}>
          {bullets.map((bullet) => (
            <Typography component="li" key={bullet} variant="body2">
              {bullet}
            </Typography>
          ))}
        </Stack>
      ) : null}
    </Alert>
  )
}

export function PageLearningPanel({
  defaultExpanded = false,
  sections,
  title = 'What am I looking at?',
}: PageLearningPanelProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <Paper
      elevation={0}
      sx={(theme) => ({
        bgcolor: theme.apiTesting.surface.elevated,
        border: '1px solid',
        borderColor: theme.apiTesting.border.default,
        borderRadius: 1.5,
        overflow: 'hidden',
      })}
      variant="outlined"
    >
      <ButtonBase
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
        sx={{
          alignItems: 'center',
          display: 'flex',
          justifyContent: 'space-between',
          p: 1.5,
          textAlign: 'left',
          width: '100%',
        }}
      >
        <Typography component="span" sx={{ fontWeight: 800 }} variant="subtitle2">
          {title}
        </Typography>
        <ExpandMoreIcon
          fontSize="small"
          sx={{
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: (theme) => theme.apiTesting.motion.transition.interactive,
          }}
        />
      </ButtonBase>
      <Collapse in={expanded}>
        <Stack spacing={1.5}>
          <Stack spacing={1.5} sx={{ px: 1.5, pb: 1.5 }}>
            {sections.map((section) => (
              <Stack key={section.title} spacing={0.5}>
                <Typography sx={{ fontWeight: 800 }} variant="body2">
                  {section.title}
                </Typography>
                <Typography color="text.secondary" variant="body2">
                  {section.body}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </Stack>
      </Collapse>
    </Paper>
  )
}
