import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithProviders } from '../../test/renderWithProviders'
import { WorkspacePage } from './WorkspacePage'

describe('WorkspacePage', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.history.replaceState({}, '', '/runs/Run%20A/workspace')
  })

  it('renders the desktop investigation cockpit and opens selected operation context', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <WorkspacePage
        runName="Run A"
        search={{ limit: 25, offset: 0, workspaceView: 'cockpit' }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /investigation workspace/i })).toBeInTheDocument()
    expect(await screen.findByRole('grid', { name: /workspace operations/i })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: /workspace graph focus/i })).toBeInTheDocument()

    await user.click(screen.getAllByRole('button', { name: /listitems/i })[0])
    expect(await screen.findByText(/selected operation/i)).toBeInTheDocument()
    expect(screen.getByText(/op-get-items/i)).toBeInTheDocument()
    expect(window.location.search).toContain('operationId=')

    await user.click(screen.getByRole('button', { name: /inspect edge/i }))
    expect(await screen.findByText(/selected edge/i)).toBeInTheDocument()
    expect(window.location.search).toContain('edgeId=edge-create-list')
    expect(window.location.search).not.toContain('operationId=')
    expect(window.location.search).not.toContain('operationKey=')
  })

  it('saves and restores URL-backed workspace views from localStorage', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <WorkspacePage
        runName="Run A"
        search={{ limit: 25, offset: 0, q: 'items', workspaceView: 'cockpit' }}
      />,
    )

    await screen.findByRole('heading', { name: /investigation workspace/i })
    await user.click(screen.getByRole('button', { name: /save view/i }))
    await user.type(screen.getByRole('textbox', { name: /view name/i }), 'Risky items')
    await user.click(screen.getByRole('button', { name: /^save$/i }))

    expect(await screen.findByRole('button', { name: /risky items/i })).toBeInTheDocument()
    expect(window.localStorage.getItem('apipilot.savedViews.v1')).toContain('Risky items')

    await user.click(screen.getByRole('button', { name: /risky items/i }))
    await waitFor(() => expect(window.location.search).toContain('savedViewId='))
  })

  it('keeps bookmarks and notes local until the export dialog opt-in is selected', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <WorkspacePage
        runName="Run A"
        search={{ limit: 25, offset: 0, operationKey: 'op-get-items', workspaceView: 'cockpit' }}
      />,
    )

    await screen.findByText(/selected operation/i)
    await user.click(screen.getByRole('button', { name: /bookmark selected/i }))
    await user.type(screen.getByRole('textbox', { name: /local note/i }), 'Review this failure')
    await user.click(screen.getByRole('button', { name: /save note/i }))
    await user.click(screen.getByRole('button', { name: /export workspace/i }))

    const preview = await screen.findByLabelText(/export preview/i)
    expect(preview).not.toHaveTextContent('Review this failure')

    await user.click(screen.getByRole('checkbox', { name: /include local notes and bookmarks/i }))
    expect(preview).toHaveTextContent('Review this failure')
  })

  it('persists desktop layout presets and offers actionable inspector recovery', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <WorkspacePage
        runName="Run A"
        search={{ limit: 25, offset: 0, workspaceView: 'cockpit' }}
      />,
    )

    expect(await screen.findByRole('heading', { name: /investigation workspace/i })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: /workspace layout preset/i })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /graph focus/i }))

    expect(window.localStorage.getItem('apipilot.layoutPresets.v1')).toContain('"layout":"graph"')
    expect(screen.getByRole('button', { name: /select first risky operation/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /select first risky operation/i }))
    expect(await screen.findByText(/selected operation/i)).toBeInTheDocument()
    expect(window.localStorage.getItem('apipilot.recentEntities.v1')).toContain('op-get-items')
  })
})
