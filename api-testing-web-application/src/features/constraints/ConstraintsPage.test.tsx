import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import { constraintExplorerEntries, invariantExplorerEntries } from '../../test/fixtures'
import { server } from '../../test/msw/server'
import { ConstraintsPage } from './ConstraintsPage'

describe('ConstraintsPage', () => {
  it('renders the explorer tab by default and maps URL-backed filters to explorer APIs', async () => {
    let requestedUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/entries', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(constraintExplorerEntries)
      }),
    )

    const { container } = renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          agreementStatus: 'both_present',
          assertionAvailable: true,
          constraintId: 'constraint-limit',
          constraintKind: 'bounds',
          constraintTab: 'explorer',
          groupBy: 'source',
          limit: 10,
          offset: 0,
          operationId: 'get-/items',
          q: 'limit',
          source: 'combined',
        }}
      />,
    )

    await screen.findByRole('grid', { name: /constraint explorer entries/i })
    await screen.findByRole('dialog', { name: /constraint detail/i })
    expect(requestedUrl?.searchParams.get('agreement_status')).toBe('both_present')
    expect(requestedUrl?.searchParams.get('assertion_available')).toBe('true')
    expect(requestedUrl?.searchParams.get('constraint_kind')).toBe('bounds')
    expect(requestedUrl?.searchParams.get('source')).toBe('combined')
    expect(screen.getByRole('tab', { name: /explorer/i })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('pm.expect(input.limit).to.be.at.least(1)')).toBeInTheDocument()

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('renders invariant explorer entries and opens URL-backed invariant detail', async () => {
    let requestedUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/constraints/invariants', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(invariantExplorerEntries)
      }),
    )

    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'invariants',
          invariantId: 'inv-limit',
          invariantKind: 'bounds',
          limit: 25,
          offset: 0,
          oracleReadiness: 'verified_runtime_oracle',
        }}
      />,
    )

    await screen.findByRole('grid', { name: /invariant explorer entries/i })
    expect(requestedUrl?.searchParams.get('invariant_kind')).toBe('bounds')
    expect(requestedUrl?.searchParams.get('oracle_readiness')).toBe('verified_runtime_oracle')
    expect(await screen.findByRole('dialog', { name: /invariant detail/i })).toBeInTheDocument()
    expect(screen.getAllByText('verified_runtime_oracle').length).toBeGreaterThan(0)
  })

  it('renders static, dynamic, and invariant query results with groups', async () => {
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'static',
          groupBy: 'section',
          limit: 25,
          offset: 0,
          q: 'limit',
          sortBy: 'operation_id',
          sortOrder: 'asc',
        }}
      />,
    )

    expect(await screen.findByText('input.limit >= 1')).toBeInTheDocument()
    expect(screen.getAllByText(/request_response/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('tab', { name: /dynamic/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /invariants/i })).toBeInTheDocument()
  })

  it('exposes URL-backed filters, group chips, row detail, and operation drawer', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'static',
          groupBy: 'section',
          limit: 10,
          offset: 0,
          operationId: 'get-/items',
          q: 'limit',
          section: 'request_response',
          sortBy: 'property_path',
          sortOrder: 'asc',
        }}
      />,
    )

    expect(await screen.findByDisplayValue('get-/items')).toBeInTheDocument()
    expect(screen.getByDisplayValue('request_response')).toBeInTheDocument()
    expect(await screen.findByRole('grid', { name: /static constraint entries/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /request_response \(1\)/i }))
    expect(window.location.search).toContain('section=request_response')

    expect(await screen.findByRole('dialog', { name: /operation detail/i })).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: /input.limit >= 1/i })[0])
    expect(await screen.findByRole('dialog', { name: /constraint detail/i })).toBeInTheDocument()
  })
})
