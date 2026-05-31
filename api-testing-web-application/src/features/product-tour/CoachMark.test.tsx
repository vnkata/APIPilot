import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '../../test/renderWithProviders'
import { CoachMark } from './CoachMark'
import type { TourDefinition } from './productTourTypes'

const richTour: TourDefinition = {
  description: 'Rich tour content',
  id: 'constraints-fundamentals',
  label: 'Constraints fundamentals',
  roles: ['qa-qc'],
  version: 2,
  steps: [
    {
      anchorId: 'constraints-header',
      body: 'Learn the first-pass model before reading generated oracle signals.',
      bullets: [
        'Source explains where the signal came from.',
        'Agreement explains whether static and runtime evidence align.',
      ],
      domainTerm: {
        definition: 'A candidate rule APIPilot may turn into executable test logic.',
        term: 'Oracle signal',
      },
      id: 'intro',
      title: 'Read constraints as oracle candidates',
      whyItMatters: 'This prevents treating every mined expression as equally reliable.',
    },
  ],
}

describe('CoachMark', () => {
  it('renders rich educational content accessibly', () => {
    renderWithProviders(
      <CoachMark
        onAction={vi.fn()}
        onBack={vi.fn()}
        onClose={vi.fn()}
        onNext={vi.fn()}
        rect={null}
        step={richTour.steps[0]}
        stepIndex={0}
        tour={richTour}
      />,
    )

    expect(screen.getByRole('dialog', { name: /read constraints as oracle candidates/i })).toBeInTheDocument()
    expect(screen.getByText(/source explains where the signal came from/i)).toBeInTheDocument()
    expect(screen.getByText(/why this matters/i)).toBeInTheDocument()
    expect(screen.getByText(/^Oracle signal$/i)).toBeInTheDocument()
    expect(screen.getByText(/candidate rule apipilot/i)).toBeInTheDocument()
  })
})
