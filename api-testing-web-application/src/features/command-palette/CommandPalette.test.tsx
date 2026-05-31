import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { renderWithProviders } from '../../test/renderWithProviders'
import { saveBookmarks, saveRecentEntities, saveSavedViews } from '../../shared/lib/workspaceStorage'
import { CommandPalette } from './CommandPalette'

describe('CommandPalette', () => {
  beforeEach(() => {
    window.localStorage.clear()
    window.history.replaceState({}, '', '/runs/Run%20A')
  })

  it('supports keyboard-first fuzzy navigation to workspace commands', async () => {
    const user = userEvent.setup()
    renderWithProviders(<CommandPalette runName="Run A" />)

    await user.keyboard('{Control>}k{/Control}')
    await screen.findByRole('dialog', { name: /command palette/i })
    await user.type(screen.getByRole('textbox', { name: /search commands/i }), 'wrkspc')
    await user.keyboard('{Enter}')

    expect(window.location.pathname).toBe('/runs/Run%20A/workspace')
  })

  it('indexes local bookmarks and saved views without backend search', async () => {
    const user = userEvent.setup()
    saveBookmarks([
      {
        createdAt: '2026-01-01T00:00:00.000Z',
        entityId: 'op-get-items',
        entityType: 'operation',
        href: '/runs/Run%20A/workspace?operationKey=op-get-items',
        id: 'bookmark-1',
        label: 'Pinned ListItems',
        runName: 'Run A',
      },
    ])
    saveSavedViews([
      {
        createdAt: '2026-01-01T00:00:00.000Z',
        id: 'view-1',
        name: 'Risky saved view',
        page: 'workspace',
        route: '/runs/Run%20A/workspace?q=items',
        runName: 'Run A',
        search: { q: 'items' },
        updatedAt: '2026-01-01T00:00:00.000Z',
      },
    ])

    renderWithProviders(<CommandPalette runName="Run A" />)
    await user.click(screen.getByRole('button', { name: /open command palette/i }))
    await user.type(screen.getByRole('textbox', { name: /search commands/i }), 'pinned')

    expect(await screen.findByRole('button', { name: /Pinned ListItems/ })).toBeInTheDocument()

    await user.clear(screen.getByRole('textbox', { name: /search commands/i }))
    await user.type(screen.getByRole('textbox', { name: /search commands/i }), 'saved')
    expect(await screen.findByRole('button', { name: /Risky saved view/ })).toBeInTheDocument()
  })

  it('indexes recent entities and compare actions as investigation shortcuts', async () => {
    const user = userEvent.setup()
    saveRecentEntities([
      {
        entityId: 'edge-create-list',
        entityType: 'graph-edge',
        href: '/runs/Run%20A/workspace?edgeId=edge-create-list',
        label: 'Recent dependency edge',
        runName: 'Run A',
        source: 'workspace',
        updatedAt: '2026-01-01T00:00:00.000Z',
      },
    ])

    renderWithProviders(<CommandPalette runName="Run A" />)
    await user.click(screen.getByRole('button', { name: /open command palette/i }))
    await user.type(screen.getByRole('textbox', { name: /search commands/i }), 'recent dependency')

    expect(await screen.findByRole('button', { name: /Recent dependency edge/ })).toBeInTheDocument()

    await user.clear(screen.getByRole('textbox', { name: /search commands/i }))
    await user.type(screen.getByRole('textbox', { name: /search commands/i }), 'open selected compare')

    expect(await screen.findByRole('button', { name: /Open current run in Compare/ })).toBeInTheDocument()
  })
})
