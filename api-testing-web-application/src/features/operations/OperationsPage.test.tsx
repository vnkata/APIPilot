import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import { operationExplorerEntries } from '../../test/fixtures'
import { server } from '../../test/msw/server'
import { OperationsPage } from './OperationsPage'

describe('OperationsPage', () => {
  it('maps URL-backed filters to explorer APIs and opens operation explorer detail', async () => {
    let entriesUrl: URL | undefined
    let facetsUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/operations/entries', ({ request }) => {
        entriesUrl = new URL(request.url)
        return HttpResponse.json(operationExplorerEntries)
      }),
      http.get('*/api/v1/runs/:runName/operations/facets', ({ request }) => {
        facetsUrl = new URL(request.url)
        return HttpResponse.json({
          has_constraints: [{ key: 'true', count: 2 }],
          has_failures: [{ key: 'true', count: 1 }],
          has_graph_edges: [{ key: 'true', count: 2 }],
          has_invariants: [{ key: 'true', count: 1 }],
          has_request_body: [{ key: 'false', count: 1 }],
          http_method: [{ key: 'get', count: 1 }],
          response_status: [{ key: '404', count: 1 }],
        })
      }),
    )

    const { container } = renderWithProviders(
      <OperationsPage
        runName="Run A"
        search={{
          groupBy: 'http_method',
          hasFailures: true,
          httpMethod: 'get',
          limit: 10,
          offset: 0,
          operationKey: 'op-get-items',
          q: 'items',
          responseStatus: '404',
          sortBy: 'constraint_count',
          sortOrder: 'desc',
        }}
      />,
    )

    await waitFor(() => expect(entriesUrl?.searchParams.get('http_method')).toBe('get'))
    expect(entriesUrl?.searchParams.get('has_failures')).toBe('true')
    expect(entriesUrl?.searchParams.get('response_status')).toBe('404')
    expect(entriesUrl?.searchParams.get('sort_by')).toBe('constraint_count')
    expect(entriesUrl?.searchParams.get('sort_order')).toBe('desc')
    expect(facetsUrl?.searchParams.get('q')).toBe('items')

    expect(await screen.findByRole('heading', { name: /operations explorer/i })).toBeInTheDocument()
    expect(screen.getByRole('grid', { name: /operation explorer entries/i })).toBeInTheDocument()
    expect(await screen.findByRole('dialog', { name: /operation explorer detail/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /graph/i })).toHaveAttribute('href', expect.stringContaining('/graph'))

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('exports only visible operation data and strips bodies unless explicitly enabled', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <OperationsPage
        runName="Run A"
        search={{ limit: 25, offset: 0, operationKey: 'op-get-items' }}
      />,
    )

    await screen.findByRole('dialog', { name: /operation explorer detail/i })
    await user.click(screen.getByRole('button', { name: /export snapshot/i }))
    const preview = await screen.findByLabelText(/export preview/i)
    expect(preview).toHaveTextContent('op-get-items')
    expect(preview).not.toHaveTextContent('request_body')

    await user.click(screen.getByRole('checkbox', { name: /include visible bodies/i }))
    expect(preview).toHaveTextContent('request_body')
  })
})
