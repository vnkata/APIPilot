import { screen } from '@testing-library/react'

import { renderWithProviders } from '../../test/renderWithProviders'

import { HttpMethodBadge, StatusCodeBadge, TestResultBadge } from './SemanticBadges'

describe('semantic API badges', () => {
  it('renders readable HTTP method labels', () => {
    renderWithProviders(<HttpMethodBadge method="post" />)

    expect(screen.getByText('POST')).toBeInTheDocument()
  })

  it('renders readable status code groups without relying on color only', () => {
    renderWithProviders(<StatusCodeBadge statusCode={404} />)

    expect(screen.getByText('404 Client error')).toBeInTheDocument()
  })

  it('renders test result counts with explicit labels', () => {
    renderWithProviders(<TestResultBadge count={3} result="failed" />)

    expect(screen.getByText('3 Failed')).toBeInTheDocument()
  })
})
