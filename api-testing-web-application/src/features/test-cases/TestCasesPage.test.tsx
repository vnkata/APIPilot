import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { http, HttpResponse } from 'msw'

import { renderWithProviders } from '../../test/renderWithProviders'
import { testCases } from '../../test/fixtures'
import { server } from '../../test/msw/server'
import { TestCasesPage } from './TestCasesPage'

describe('TestCasesPage', () => {
  it('renders test cases and exposes the include body safety toggle', async () => {
    const user = userEvent.setup()
    renderWithProviders(<TestCasesPage runName="Run A" search={{ includeBody: false, limit: 25, offset: 0 }} />)

    expect(await screen.findByText('tc-1')).toBeInTheDocument()
    const toggle = screen.getByRole('checkbox', { name: /include sanitized bodies/i })
    expect(toggle).not.toBeChecked()

    await user.click(toggle)
    expect(window.location.search).toContain('includeBody=true')
  })

  it('opens URL-backed operation details and exports bodies only after explicit opt-in', async () => {
    const user = userEvent.setup()
    renderWithProviders(
      <TestCasesPage
        runName="Run A"
        search={{ includeBody: true, limit: 25, offset: 0, operationId: 'get-/items' }}
      />,
    )

    await user.click(await screen.findByRole('button', { name: /get-\/items/i }))
    expect(await screen.findByRole('complementary', { name: /operation detail/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /export snapshot/i }))
    const preview = await screen.findByLabelText(/export preview/i)
    expect(preview).not.toHaveTextContent('response_body')

    await user.click(screen.getByRole('checkbox', { name: /include visible bodies/i }))
    expect(preview).toHaveTextContent('response_body')
  })

  it('opens URL-backed test case details and keeps body sections gated by includeBody', async () => {
    let requestedUrl: URL | undefined
    server.use(
      http.get('*/api/v1/runs/:runName/test-cases', ({ request }) => {
        requestedUrl = new URL(request.url)
        return HttpResponse.json(testCases)
      }),
    )

    const { container } = renderWithProviders(
      <TestCasesPage
        runName="Run A"
        search={{
          includeBody: false,
          limit: 10,
          offset: 0,
          operationId: 'get-/items',
          statusCode: 200,
          testCaseId: 'tc-1',
        }}
      />,
    )

    await waitFor(() => expect(requestedUrl?.searchParams.get('operation_id')).toBe('get-/items'))
    expect(requestedUrl?.searchParams.get('status_code')).toBe('200')
    expect(requestedUrl?.searchParams.get('limit')).toBe('10')
    const inspector = await screen.findByRole('complementary', { name: /test case detail/i })
    expect(within(inspector).getByText('tc-1')).toBeInTheDocument()
    expect(screen.queryByText(/response body/i)).not.toBeInTheDocument()

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
