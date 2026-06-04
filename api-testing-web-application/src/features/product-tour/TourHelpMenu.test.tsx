import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { renderWithProviders } from '../../test/renderWithProviders'
import { TourHelpMenu } from './TourHelpMenu'

describe('TourHelpMenu', () => {
  it('lists all contextual tours for a dense education page', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TourHelpMenu pathname="/runs/Run%20A/constraints" />)

    await user.click(screen.getByRole('button', { name: /open guided tours/i }))

    expect(screen.getByRole('menuitem', { name: /start apipilot workspace/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /start constraints fundamentals/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /start constraints workbench/i })).toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: /start constraints explorer/i })).toBeInTheDocument()
  })

  it('starts the selected contextual tour from the menu', async () => {
    const user = userEvent.setup()
    const { store } = renderWithProviders(<TourHelpMenu pathname="/builder/run-configs/new" />)

    await user.click(screen.getByRole('button', { name: /open guided tours/i }))
    await user.click(screen.getByRole('menuitem', { name: /start run config builder/i }))

    expect(store.getState().productTour.activeTourId).toBe('builder-run-config')
  })

  it('starts Combination HITL activation from constraints routes', async () => {
    const user = userEvent.setup()
    const { store } = renderWithProviders(<TourHelpMenu pathname="/runs/Run%20A/constraints" />)

    await user.click(screen.getByRole('button', { name: /open guided tours/i }))
    await user.click(screen.getByRole('menuitem', { name: /start combination hitl activation/i }))

    expect(store.getState().activationOnboarding.progressByRunName['Run A']?.active).toBe(true)
    expect(window.location.pathname).toBe('/runs/Run%20A/constraints')
    expect(window.location.search).toContain('constraintTab=combination')
    expect(window.location.search).toContain('constraintsView=table')
  })
})
