import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithProviders } from '../../test/renderWithProviders'
import { ConstraintsPage } from './ConstraintsPage'

describe('ConstraintsPage', () => {
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
