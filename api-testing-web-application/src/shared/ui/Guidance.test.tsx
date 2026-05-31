import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderWithProviders } from '../../test/renderWithProviders'
import {
  DomainTermTooltip,
  GuidanceCallout,
  InfoHint,
  PageLearningPanel,
} from './Guidance'

describe('Guidance primitives', () => {
  it('renders accessible inline hints and domain terms', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <>
        <InfoHint label="Source help" title="Source tells where APIPilot found the signal." />
        <DomainTermTooltip definition="A generated rule candidate that can become an assertion." term="Oracle signal" />
      </>,
    )

    await user.hover(screen.getByLabelText(/source help/i))
    expect(await screen.findByText(/where apipilot found the signal/i)).toBeInTheDocument()
    await user.hover(screen.getByText(/oracle signal/i))
    expect(await screen.findByText(/generated rule candidate/i)).toBeInTheDocument()
  })

  it('renders callout and collapsible page learning content', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <>
        <GuidanceCallout
          bullets={['Start with high-confidence signals.', 'Open details before exporting.']}
          title="How to triage"
        />
        <PageLearningPanel
          sections={[
            {
              body: 'Source and agreement explain trust.',
              title: 'Read the row',
            },
            {
              body: 'Assertion readiness explains whether a signal can become a test oracle.',
              title: 'Decide next action',
            },
          ]}
          title="What am I looking at?"
        />
      </>,
    )

    expect(screen.getByText(/start with high-confidence signals/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /what am i looking at/i }))
    expect(screen.getByText(/source and agreement explain trust/i)).toBeInTheDocument()
    expect(screen.getByText(/assertion readiness explains/i)).toBeInTheDocument()
  })
})
