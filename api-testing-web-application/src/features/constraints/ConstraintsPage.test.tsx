import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import { constraintExplorerEntries, invariantExplorerEntries } from '../../test/fixtures'
import { server } from '../../test/msw/server'
import { ConstraintsPage } from './ConstraintsPage'

describe('ConstraintsPage', () => {
  it('renders workbench by default with current-page triage and no accessibility violations', async () => {
    const { container } = renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /constraint workbench/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/constraint workspace summary/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/constraint workbench start here/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /top constraint signals/i })).toBeInTheDocument()
    expect(screen.getAllByText(/current page/i).length).toBeGreaterThan(0)
    expect(await screen.findByText(/input.limit >= 1/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /workbench/i })).toHaveAttribute('aria-pressed', 'true')

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  }, 10_000)

  it('renders the explorer table mode and maps URL-backed filters to explorer APIs', async () => {
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
          constraintsView: 'table',
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
    await screen.findByRole('complementary', { name: /constraint detail/i })
    expect(requestedUrl?.searchParams.get('agreement_status')).toBe('both_present')
    expect(requestedUrl?.searchParams.get('assertion_available')).toBe('true')
    expect(requestedUrl?.searchParams.get('constraint_kind')).toBe('bounds')
    expect(requestedUrl?.searchParams.get('source')).toBe('combined')
    expect(screen.getByRole('button', { name: /explorer/i })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText(/Minimum bound/i)).toBeInTheDocument()

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
          constraintsView: 'table',
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
    expect(await screen.findByRole('complementary', { name: /invariant detail/i })).toBeInTheDocument()
    expect(screen.getAllByText('verified_runtime_oracle').length).toBeGreaterThan(0)
  })

  it('renders static, dynamic, and invariant query results with groups', async () => {
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'static',
          constraintsView: 'table',
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
    expect(screen.getByRole('button', { name: /dynamic/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /invariants/i })).toBeInTheDocument()
  })

  it('exposes URL-backed filters, advanced group chips, row detail, and operation drawer', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'static',
          constraintsView: 'table',
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

    await user.click(screen.getByRole('button', { name: /advanced filters/i }))
    expect(await screen.findByRole('dialog', { name: /advanced constraint filters/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /request_response \(1\)/i }))
    expect(window.location.search).toContain('section=request_response')
    await user.click(screen.getByRole('button', { name: /^done$/i }))

    expect(await screen.findByRole('complementary', { name: /operation detail/i })).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: /input.limit >= 1/i })[0])
    expect(await screen.findByRole('complementary', { name: /constraint detail/i })).toBeInTheDocument()
  })

  it('renders matrix mode for oracle readiness triage', async () => {
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          constraintsView: 'matrix',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /readiness matrix/i })).toBeInTheDocument()
    expect(screen.getAllByText(/current page/i).length).toBeGreaterThan(0)
    await waitFor(() => expect(screen.getAllByText(/both_present/i).length).toBeGreaterThan(0))
    expect(screen.getByText(/assertion evidence/i)).toBeInTheDocument()
  })

  it('keeps primary filters URL-backed while clear filters resets query state', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
          q: 'limit',
        }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /constraint workbench/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /combined 1/i }))
    expect(window.location.search).toContain('source=combined')

    await user.clear(screen.getByRole('textbox', { name: /search constraints/i }))
    await user.type(screen.getByRole('textbox', { name: /search constraints/i }), 'date')
    await user.tab()
    expect(window.location.search).toContain('q=date')

    await user.click(screen.getByRole('button', { name: /clear filters/i }))
    expect(window.location.search).not.toContain('q=')
    expect(window.location.search).not.toContain('source=')
  })

  it('switches top segmented modes through URL-backed params', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    await screen.findByRole('heading', { name: /constraint workbench/i })
    await user.click(screen.getByRole('button', { name: /^Explorer$/i }))

    expect(window.location.search).toContain('constraintsView=table')
    expect(window.location.search).toContain('constraintTab=explorer')
  })

  it('renders readable constraint detail by default and raw fields when requested', async () => {
    const { rerender } = renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintId: 'constraint-limit',
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('complementary', { name: /constraint detail/i })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: /how to read this/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /source lineage/i })).toBeInTheDocument()
    expect(screen.getByText(/Text matches static expression/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Minimum bound/i).length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /raw fields/i })).toBeInTheDocument()

    rerender(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintDetailView: 'raw',
          constraintId: 'constraint-limit',
          constraintTab: 'explorer',
          constraintsView: 'workbench',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByLabelText(/constraint raw fields/i)).toBeInTheDocument()
  })

  it('renders readable invariant evidence detail', async () => {
    renderWithProviders(
      <ConstraintsPage
        runName="Run A"
        search={{
          constraintTab: 'invariants',
          constraintsView: 'table',
          invariantId: 'inv-limit',
          limit: 25,
          offset: 0,
        }}
      />,
    )

    expect(await screen.findByRole('complementary', { name: /invariant detail/i })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: /correlation evidence/i })).toBeInTheDocument()
    expect(screen.getByText(/property path matched input.limit/i)).toBeInTheDocument()
    expect(screen.getByText(/Minimum bound/i)).toBeInTheDocument()
  })
})
