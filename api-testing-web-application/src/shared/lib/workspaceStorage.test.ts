import {
  apipilotBookmarksStorageKey,
  apipilotLayoutPresetsStorageKey,
  apipilotRecentEntitiesStorageKey,
  apipilotSavedViewsStorageKey,
  apipilotTablePowerPresetsStorageKey,
  apipilotTableLayoutsStorageKey,
  apipilotWorkspaceNotesStorageKey,
  loadBookmarks,
  loadLayoutPresets,
  loadRecentEntities,
  loadSavedViews,
  loadTablePowerPresets,
  loadTableLayouts,
  loadWorkspaceNotes,
  saveBookmarks,
  saveLayoutPresets,
  saveRecentEntities,
  saveSavedViews,
  saveTablePowerPresets,
  saveTableLayouts,
  saveWorkspaceNotes,
  upsertBookmark,
  upsertLayoutPreset,
  upsertRecentEntity,
  upsertSavedView,
  upsertTablePowerPreset,
  upsertWorkspaceNote,
} from './workspaceStorage'

describe('workspaceStorage', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('loads empty collections when localStorage is missing or invalid', () => {
    window.localStorage.setItem(apipilotSavedViewsStorageKey, '{broken')
    window.localStorage.setItem(apipilotBookmarksStorageKey, '{"items":[{"broken":true}]}')
    window.localStorage.setItem(apipilotWorkspaceNotesStorageKey, '[]')
    window.localStorage.setItem(apipilotTableLayoutsStorageKey, '{"version":99,"items":[]}')
    window.localStorage.setItem(apipilotLayoutPresetsStorageKey, '{"version":99,"items":[]}')
    window.localStorage.setItem(apipilotRecentEntitiesStorageKey, '{broken')
    window.localStorage.setItem(apipilotTablePowerPresetsStorageKey, '[]')

    expect(loadSavedViews()).toEqual([])
    expect(loadBookmarks()).toEqual([])
    expect(loadWorkspaceNotes()).toEqual([])
    expect(loadTableLayouts()).toEqual([])
    expect(loadLayoutPresets()).toEqual([])
    expect(loadRecentEntities()).toEqual([])
    expect(loadTablePowerPresets()).toEqual([])
  })

  it('persists saved views, bookmarks, notes, and table layouts with versioned schemas', () => {
    saveSavedViews([
      {
        createdAt: '2026-01-01T00:00:00.000Z',
        id: 'view-1',
        name: 'Risky operations',
        page: 'workspace',
        route: '/runs/Run%20A/workspace?q=items',
        runName: 'Run A',
        search: { q: 'items', workspaceView: 'cockpit' },
        updatedAt: '2026-01-01T00:00:00.000Z',
      },
    ])
    saveBookmarks([
      {
        createdAt: '2026-01-01T00:00:00.000Z',
        entityId: 'op-get-items',
        entityType: 'operation',
        href: '/runs/Run%20A/workspace?operationKey=op-get-items',
        id: 'bookmark-1',
        label: 'ListItems',
        runName: 'Run A',
      },
    ])
    saveWorkspaceNotes([
      {
        createdAt: '2026-01-01T00:00:00.000Z',
        entityId: 'op-get-items',
        entityType: 'operation',
        id: 'note-1',
        note: 'Review failure evidence',
        runName: 'Run A',
        updatedAt: '2026-01-01T00:00:00.000Z',
      },
    ])
    saveTableLayouts([
      {
        columnVisibilityModel: { response_statuses: false },
        id: 'Run A:workspace:operations',
        page: 'workspace',
        runName: 'Run A',
        tableId: 'operations',
        updatedAt: '2026-01-01T00:00:00.000Z',
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
        entityId: 'op-get-items',
        entityType: 'operation',
        href: '/runs/Run%20A/workspace?operationKey=op-get-items',
        label: 'ListItems',
        runName: 'Run A',
        source: 'workspace',
        updatedAt: '2026-01-01T00:00:00.000Z',
      },
    ])
    saveTablePowerPresets([
      {
        columnVisibilityModel: { response_statuses: false },
        id: 'table-power:run-a:workspace:operations:default',
        name: 'Default',
        page: 'workspace',
        runName: 'Run A',
        tableId: 'operations',
        updatedAt: '2026-01-01T00:00:00.000Z',
      },
    ])

    expect(loadSavedViews()).toHaveLength(1)
    expect(loadBookmarks()).toHaveLength(1)
    expect(loadWorkspaceNotes()).toHaveLength(1)
    expect(loadTableLayouts()).toHaveLength(1)
    expect(loadLayoutPresets()).toHaveLength(1)
    expect(loadRecentEntities()).toHaveLength(1)
    expect(loadTablePowerPresets()).toHaveLength(1)
  })

  it('upserts records by stable ids and updates timestamps without duplicating', () => {
    const firstSavedViews = upsertSavedView([], {
      name: 'Risky operations',
      page: 'workspace',
      route: '/runs/Run%20A/workspace?q=items',
      runName: 'Run A',
      search: { q: 'items' },
    }, '2026-01-01T00:00:00.000Z')
    const nextSavedViews = upsertSavedView(firstSavedViews, {
      id: firstSavedViews[0].id,
      name: 'Risky GET operations',
      page: 'workspace',
      route: '/runs/Run%20A/workspace?q=get',
      runName: 'Run A',
      search: { q: 'get' },
    }, '2026-01-02T00:00:00.000Z')

    expect(nextSavedViews).toHaveLength(1)
    expect(nextSavedViews[0]).toMatchObject({
      createdAt: '2026-01-01T00:00:00.000Z',
      name: 'Risky GET operations',
      updatedAt: '2026-01-02T00:00:00.000Z',
    })

    expect(upsertBookmark([], {
      entityId: 'op-get-items',
      entityType: 'operation',
      href: '/runs/Run%20A/workspace?operationKey=op-get-items',
      label: 'ListItems',
      runName: 'Run A',
    }, '2026-01-01T00:00:00.000Z')).toHaveLength(1)

    expect(upsertWorkspaceNote([], {
      entityId: 'op-get-items',
      entityType: 'operation',
      note: 'Check 404 path',
      runName: 'Run A',
    }, '2026-01-01T00:00:00.000Z')[0]).toMatchObject({
      entityId: 'op-get-items',
      note: 'Check 404 path',
    })

    expect(upsertLayoutPreset([], {
      layout: 'inspector',
      page: 'workspace',
      runName: 'Run A',
    }, '2026-01-01T00:00:00.000Z')[0]).toMatchObject({
      id: 'layout:run-a:workspace',
      layout: 'inspector',
    })

    expect(upsertRecentEntity([], {
      entityId: 'edge-create-list',
      entityType: 'graph-edge',
      href: '/runs/Run%20A/workspace?edgeId=edge-create-list',
      label: 'post-/items -> get-/items',
      runName: 'Run A',
      source: 'workspace',
    }, '2026-01-01T00:00:00.000Z')[0]).toMatchObject({
      entityId: 'edge-create-list',
      source: 'workspace',
    })

    expect(upsertTablePowerPreset([], {
      columnVisibilityModel: { response_statuses: false },
      name: 'Compact triage',
      page: 'operations',
      runName: 'Run A',
      tableId: 'operations',
    }, '2026-01-01T00:00:00.000Z')[0]).toMatchObject({
      id: 'table-power:run-a:operations:operations:compact-triage',
      name: 'Compact triage',
    })
  })
})
