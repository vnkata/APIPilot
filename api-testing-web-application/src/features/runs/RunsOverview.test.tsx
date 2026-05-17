import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import { server } from '../../test/msw/server'
import { RunOverviewPage } from './RunOverviewPage'
import { RunsPage } from './RunsPage'

describe('runs vertical slice', () => {
  it('renders available runs from the generated API boundary', async () => {
    renderWithProviders(<RunsPage />)

    expect(screen.getByRole('heading', { name: /runs/i })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /Run A/i })).toHaveAttribute(
      'href',
      '/runs/Run%20A',
    )
  })

  it('renders summary metrics and artifact availability for the selected run', async () => {
    renderWithProviders(<RunOverviewPage runName="Run A" />)

    expect(await screen.findByText('Run A')).toBeInTheDocument()
    expect(screen.getByText(/Operations/i)).toBeInTheDocument()
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Artifacts/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/static_constraints/i)).toBeInTheDocument()
  })

  it('renders command center mode for QA triage drilldown', async () => {
    renderWithProviders(<RunOverviewPage runName="Run A" search={{ overviewView: 'command' }} />)

    expect(await screen.findByRole('heading', { name: /qa mission control/i })).toBeInTheDocument()
    expect(screen.getByText(/next best inspection/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /review risky operations/i })).toHaveAttribute(
      'href',
      expect.stringContaining('/operations'),
    )
    expect(screen.getAllByText(/failure signal/i).length).toBeGreaterThan(0)
  })

  it('shows recoverable API errors without crashing the workspace', async () => {
    server.use(
      http.get('*/api/v1/runs/:runName/summary', () =>
        HttpResponse.json(
          { error: { code: 'not_found', message: 'Run missing was not found' } },
          { status: 404 },
        ),
      ),
    )

    renderWithProviders(<RunOverviewPage runName="missing" />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/not found/i)
  })

  it('keeps selected run navigation URL-backed', async () => {
    const user = userEvent.setup()
    renderWithProviders(<RunsPage />)

    const runLink = await screen.findByRole('link', { name: /Run A/i })
    await user.click(runLink)

    await waitFor(() => expect(window.location.pathname).toBe('/runs/Run%20A'))
  })
})
