import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { reportEntries } from '../../test/fixtures'
import { server } from '../../test/msw/server'
import { renderWithProviders } from '../../test/renderWithProviders'
import { ReportsPage } from './ReportsPage'

describe('ReportsPage', () => {
  it('renders status chart and report entries', async () => {
    renderWithProviders(<ReportsPage runName="Run A" search={{ limit: 25, offset: 0 }} />)

    expect((await screen.findAllByText(/Status distribution/i)).length).toBeGreaterThan(0)
    expect((await screen.findAllByText(/404 Client error/)).length).toBeGreaterThan(0)
    expect(screen.getByRole('grid', { name: /report entries/i })).toBeInTheDocument()
  })

  it('maps URL-backed report filters to backend query params and opens operation details', async () => {
    const user = userEvent.setup()
    const requests: URL[] = []
    server.use(
      http.get('*/api/v1/runs/:runName/reports/entries', ({ request }) => {
        requests.push(new URL(request.url))
        return HttpResponse.json(reportEntries)
      }),
    )

    renderWithProviders(
      <ReportsPage
        runName="Run A"
        search={{
          groupBy: 'operation_id',
          limit: 10,
          offset: 10,
          operationId: 'get-/items',
          q: '404',
          sortBy: 'count',
          sortOrder: 'desc',
          statusCode: '404',
        }}
      />,
    )

    expect(await screen.findByDisplayValue('get-/items')).toBeInTheDocument()
    expect(screen.getAllByDisplayValue('404').length).toBeGreaterThan(0)
    expect(requests.at(-1)?.searchParams.get('operation_id')).toBe('get-/items')
    expect(requests.at(-1)?.searchParams.get('status_code')).toBe('404')
    expect(requests.at(-1)?.searchParams.get('sort_by')).toBe('count')
    expect(requests.at(-1)?.searchParams.get('group_by')).toBe('operation_id')

    await user.click(screen.getAllByRole('button', { name: /get-\/items/i })[0])
    expect(await screen.findByRole('complementary', { name: /operation detail/i })).toBeInTheDocument()
    expect(screen.getByText('ListItems')).toBeInTheDocument()
  })
})
