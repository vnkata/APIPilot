import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { renderWithProviders } from '../../test/renderWithProviders'
import { createAppStore } from '../../app/store'
import { setTourEventEmitter, type TourEventEmitter } from './tourAnalytics'
import { ProductTourHost } from './ProductTourHost'
import { TOUR_ANCHORS, tourAnchor } from './tourAnchors'

let mockedPathname = '/runs/Run%20A/constraints'

vi.mock('@tanstack/react-router', () => ({
  useLocation: () => ({ pathname: mockedPathname }),
}))

describe('ProductTourHost', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    mockedPathname = '/runs/Run%20A/constraints'
  })

  it('shows a contextual prompt and runs an accessible guided tour', async () => {
    const user = userEvent.setup()
    const events: Parameters<TourEventEmitter>[0][] = []
    const restoreEmitter = setTourEventEmitter((event) => events.push(event))
    renderWithProviders(
      <>
        <main>
          <section {...tourAnchor(TOUR_ANCHORS.constraintsHeader)}>Constraints header</section>
          <section {...tourAnchor(TOUR_ANCHORS.constraintsFilters)}>Constraints filters</section>
          <section {...tourAnchor(TOUR_ANCHORS.constraintsWorkbench)}>Constraints workbench</section>
          <section {...tourAnchor(TOUR_ANCHORS.constraintsMatrix)}>Constraints matrix</section>
        </main>
        <ProductTourHost />
      </>,
    )

    expect(await screen.findByRole('region', { name: /constraints tour prompt/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /start tour/i }))

    expect(await screen.findByRole('dialog', { name: /read constraints as oracle candidates/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/tour progress/i)).toBeInTheDocument()
    expect(screen.getByText(/why this matters/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^next$/i }))
    expect(await screen.findByRole('dialog', { name: /source is your first trust signal/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^back$/i }))
    expect(await screen.findByRole('dialog', { name: /read constraints as oracle candidates/i })).toBeInTheDocument()

    const results = await axe(document.body)
    expect(results).toHaveNoViolations()
    expect(events.some((event) => event.type === 'prompt_shown')).toBe(true)
    expect(events.some((event) => event.type === 'tour_started')).toBe(true)
    expect(events.some((event) => event.type === 'step_viewed')).toBe(true)
    restoreEmitter()
  })

  it('completes the tour and persists completion state', async () => {
    const user = userEvent.setup()
    const { store } = renderWithProviders(
      <>
        <section {...tourAnchor(TOUR_ANCHORS.constraintsHeader)}>Constraints header</section>
        <section {...tourAnchor(TOUR_ANCHORS.constraintsFilters)}>Constraints filters</section>
        <section {...tourAnchor(TOUR_ANCHORS.constraintsWorkbench)}>Constraints workbench</section>
        <section {...tourAnchor(TOUR_ANCHORS.constraintsMatrix)}>Constraints matrix</section>
        <ProductTourHost />
      </>,
    )

    await user.click(await screen.findByRole('button', { name: /start tour/i }))
    await user.click(await screen.findByRole('button', { name: /^next$/i }))
    await user.click(await screen.findByRole('button', { name: /^next$/i }))
    await user.click(await screen.findByRole('button', { name: /^next$/i }))
    await user.click(await screen.findByRole('button', { name: /^next$/i }))
    await user.click(await screen.findByRole('button', { name: /^next$/i }))
    await user.click(await screen.findByRole('button', { name: /^next$/i }))
    await user.click(await screen.findByRole('button', { name: /^finish$/i }))

    await waitFor(() => {
      expect(store.getState().productTour.progressByTourId['constraints-fundamentals']?.completedVersion).toBe(2)
    })
  })

  it('shows a missing-target fallback instead of crashing', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <>
        <section {...tourAnchor(TOUR_ANCHORS.constraintsHeader)}>Constraints header</section>
        <ProductTourHost />
      </>,
    )

    await user.click(await screen.findByRole('button', { name: /start tour/i }))
    await user.click(await screen.findByRole('button', { name: /^next$/i }))

    expect(await screen.findByText(/tour target is not visible/i)).toBeInTheDocument()
  })

  it('offers first-time learning paths and starts the selected path tour', async () => {
    mockedPathname = '/runs'
    const user = userEvent.setup()
    const store = createAppStore({
      productTour: {
        dismissedPromptByTourId: {
          runs: 2,
        },
        progressByTourId: {},
        role: 'qa-qc',
      },
    })
    renderWithProviders(<ProductTourHost />, { store })

    expect(await screen.findByRole('region', { name: /new to apipilot/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /build a new run/i }))

    expect(store.getState().productTour.activeTourId).toBe('builder-specs')
    expect(window.location.pathname).toBe('/builder/specs')
  })
})
