import type { Meta, StoryObj } from '@storybook/react-vite'

import { CommandPalette } from '../features/command-palette/CommandPalette'
import { WorkspacePage } from '../features/workspace/WorkspacePage'
import {
  saveBookmarks,
  saveLayoutPresets,
  saveRecentEntities,
  saveSavedViews,
} from '../shared/lib/workspaceStorage'
import { ExportSnapshotDialog } from '../shared/ui/ExportSnapshotDialog'

const meta = {
  title: 'Investigation/Workspace Tools',
} satisfies Meta

export default meta

type Story = StoryObj

function seedWorkspaceLocalState() {
  if (typeof window === 'undefined') return
  saveSavedViews([
    {
      createdAt: '2026-01-01T00:00:00.000Z',
      id: 'story-risky-items',
      name: 'Risky items',
      page: 'workspace',
      route: '/runs/Run%20A/workspace?q=items&operationKey=op-get-items',
      runName: 'Run A',
      search: { operationKey: 'op-get-items', q: 'items', workspaceView: 'cockpit' },
      updatedAt: '2026-01-01T00:00:00.000Z',
    },
  ])
  saveBookmarks([
    {
      createdAt: '2026-01-01T00:00:00.000Z',
      entityId: 'op-get-items',
      entityType: 'operation',
      href: '/runs/Run%20A/workspace?operationKey=op-get-items',
      id: 'story-bookmark-list-items',
      label: 'Pinned ListItems',
      runName: 'Run A',
    },
  ])
  saveLayoutPresets([
    {
      id: 'layout:run-a:workspace',
      layout: 'graph',
      page: 'workspace',
      runName: 'Run A',
      updatedAt: '2026-01-01T00:00:00.000Z',
    },
  ])
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
}

export const SavedViewsWorkspace: Story = {
  render: () => {
    seedWorkspaceLocalState()
    return (
      <WorkspacePage
        runName="Run A"
        search={{ limit: 25, offset: 0, operationKey: 'op-get-items', workspaceView: 'cockpit' }}
      />
    )
  },
}

export const CommandPaletteLauncher: Story = {
  render: () => {
    seedWorkspaceLocalState()
    return <CommandPalette runName="Run A" />
  },
}

export const GraphFocusWorkspace: Story = {
  render: () => {
    seedWorkspaceLocalState()
    return (
      <WorkspacePage
        runName="Run A"
        search={{ edgeId: 'edge-create-list', limit: 25, offset: 0, workspaceView: 'cockpit' }}
      />
    )
  },
}

export const ExportStudio: Story = {
  render: () => (
    <ExportSnapshotDialog
      data={{
        rows: [
          {
            authorization: 'Bearer story-token',
            request_body: { password: 'hidden' },
            status_code: 200,
          },
        ],
      }}
      filters={{ operationKey: 'op-get-items' }}
      localContext={{
        bookmarks: [{ label: 'Pinned ListItems' }],
        notes: [{ note: 'Local-only story note', token: 'story-secret' }],
      }}
      localContextLabel="local notes and bookmarks"
      onClose={() => undefined}
      open
      route="/runs/Run%20A/workspace?operationKey=op-get-items"
      selectedContext={{ operation_id: 'get-/items' }}
      title="Workspace"
    />
  ),
}
