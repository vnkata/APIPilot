import type { Meta, StoryObj } from '@storybook/react-vite'
import { Stack, Typography } from '@mui/material'

import { CoachMark } from '../features/product-tour/CoachMark'
import type { TourDefinition } from '../features/product-tour/productTourTypes'
import {
  DomainTermTooltip,
  GuidanceCallout,
  InfoHint,
  PageLearningPanel,
} from '../shared/ui/Guidance'

const richTour: TourDefinition = {
  description: 'Story tour for rich coach mark content.',
  id: 'constraints-fundamentals',
  label: 'Constraints tour',
  roles: ['qa-qc'],
  version: 2,
  steps: [
    {
      anchorId: 'constraints-header',
      body: 'Constraints and invariants are generated oracle candidates, not automatically final test truth.',
      bullets: [
        'Source explains where evidence came from.',
        'Agreement explains whether evidence aligns.',
        'Assertion readiness explains executable potential.',
      ],
      domainTerm: {
        definition: 'A generated rule candidate that may become executable test logic.',
        term: 'Oracle signal',
      },
      id: 'story-step',
      title: 'Read constraints as oracle candidates',
      whyItMatters: 'This keeps first-time users from trusting every generated expression equally.',
    },
  ],
}

const meta = {
  title: 'Guidance/Native Education',
} satisfies Meta

export default meta

type Story = StoryObj

export const RichCoachMark: Story = {
  render: () => (
    <CoachMark
      onAction={() => undefined}
      onBack={() => undefined}
      onClose={() => undefined}
      onNext={() => undefined}
      rect={null}
      step={richTour.steps[0]}
      stepIndex={0}
      tour={richTour}
    />
  ),
}

export const PageLearning: Story = {
  render: () => (
    <Stack spacing={2} sx={{ maxWidth: 720 }}>
      <GuidanceCallout
        bullets={[
          'Start with the domain concept.',
          'Use the tooltip only for quick reminders.',
          'Open the learning panel for workflow guidance.',
        ]}
        title="Guided UX pattern"
      />
      <PageLearningPanel
        defaultExpanded
        sections={[
          {
            body: 'Source, agreement, and assertion readiness are the first three concepts to explain on the Constraints page.',
            title: 'Teach the vocabulary',
          },
          {
            body: 'Keep advanced details collapsible so desktop users can scan without losing help.',
            title: 'Keep the page dense but learnable',
          },
        ]}
      />
      <Typography>
        <DomainTermTooltip
          definition="A generated rule candidate that may become executable test logic."
          term="Oracle signal"
        />{' '}
        <InfoHint label="Oracle signal help" title="Use detail evidence before trusting a generated oracle signal." />
      </Typography>
    </Stack>
  ),
}
