import { screen } from '@testing-library/react'

import { renderWithProviders } from '../../test/renderWithProviders'
import { BackendHealthChip } from './BackendHealthChip'

describe('BackendHealthChip', () => {
  it('shows backend health status from the generated health endpoint', async () => {
    renderWithProviders(<BackendHealthChip />)

    expect(await screen.findByText('Backend ok')).toBeInTheDocument()
  })
})
