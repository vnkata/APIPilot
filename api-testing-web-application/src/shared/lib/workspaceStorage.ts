import { z } from 'zod'

export const apipilotSavedViewsStorageKey = 'apipilot.savedViews.v1'
export const apipilotBookmarksStorageKey = 'apipilot.bookmarks.v1'
export const apipilotWorkspaceNotesStorageKey = 'apipilot.workspaceNotes.v1'
export const apipilotTableLayoutsStorageKey = 'apipilot.tableLayouts.v1'
export const apipilotLayoutPresetsStorageKey = 'apipilot.layoutPresets.v1'
export const apipilotRecentEntitiesStorageKey = 'apipilot.recentEntities.v1'
export const apipilotTablePowerPresetsStorageKey = 'apipilot.tablePowerPresets.v1'

const storageVersion = 1

const searchValueSchema = z.union([z.boolean(), z.number(), z.string(), z.null()]).optional()
const searchSchema = z.record(z.string(), searchValueSchema).catch({})

export type WorkspacePageId =
  | 'artifacts'
  | 'compare'
  | 'constraints'
  | 'graph'
  | 'history'
  | 'operations'
  | 'reports'
  | 'test-cases'
  | 'workspace'

export type WorkspaceEntityType =
  | 'artifact'
  | 'constraint'
  | 'graph-edge'
  | 'graph-sequence'
  | 'invariant'
  | 'operation'
  | 'test-case'

export type WorkspaceLayoutPreset = 'balanced' | 'graph' | 'inspector' | 'table'

export type RecentEntitySource = 'builder' | 'compare' | 'graph' | 'operations' | 'workspace'

export type SavedView = {
  createdAt: string
  id: string
  name: string
  page: WorkspacePageId
  route: string
  runName: string
  search: Record<string, boolean | number | string | null | undefined>
  updatedAt: string
}

export type WorkspaceBookmark = {
  createdAt: string
  entityId: string
  entityType: WorkspaceEntityType
  href: string
  id: string
  label: string
  runName: string
}

export type WorkspaceNote = {
  createdAt: string
  entityId: string
  entityType: WorkspaceEntityType
  id: string
  note: string
  runName: string
  updatedAt: string
}

export type TableLayout = {
  columnVisibilityModel: Record<string, boolean>
  id: string
  page: WorkspacePageId
  runName: string
  tableId: string
  updatedAt: string
}

export type LayoutPreset = {
  id: string
  layout: WorkspaceLayoutPreset
  page: WorkspacePageId
  runName: string
  updatedAt: string
}

export type RecentEntity = {
  entityId: string
  entityType: WorkspaceEntityType
  href: string
  label: string
  runName: string
  source: RecentEntitySource
  updatedAt: string
}

export type TablePowerPreset = {
  columnVisibilityModel: Record<string, boolean>
  id: string
  name: string
  page: WorkspacePageId
  runName: string
  tableId: string
  updatedAt: string
}

const savedViewSchema: z.ZodType<SavedView> = z.object({
  createdAt: z.string(),
  id: z.string().min(1),
  name: z.string().min(1),
  page: z.enum(['artifacts', 'compare', 'constraints', 'graph', 'history', 'operations', 'reports', 'test-cases', 'workspace']),
  route: z.string().min(1),
  runName: z.string().min(1),
  search: searchSchema,
  updatedAt: z.string(),
})

const bookmarkSchema: z.ZodType<WorkspaceBookmark> = z.object({
  createdAt: z.string(),
  entityId: z.string().min(1),
  entityType: z.enum(['artifact', 'constraint', 'graph-edge', 'graph-sequence', 'invariant', 'operation', 'test-case']),
  href: z.string().min(1),
  id: z.string().min(1),
  label: z.string().min(1),
  runName: z.string().min(1),
})

const noteSchema: z.ZodType<WorkspaceNote> = z.object({
  createdAt: z.string(),
  entityId: z.string().min(1),
  entityType: z.enum(['artifact', 'constraint', 'graph-edge', 'graph-sequence', 'invariant', 'operation', 'test-case']),
  id: z.string().min(1),
  note: z.string(),
  runName: z.string().min(1),
  updatedAt: z.string(),
})

const tableLayoutSchema: z.ZodType<TableLayout> = z.object({
  columnVisibilityModel: z.record(z.string(), z.boolean()).catch({}),
  id: z.string().min(1),
  page: z.enum(['artifacts', 'compare', 'constraints', 'graph', 'history', 'operations', 'reports', 'test-cases', 'workspace']),
  runName: z.string().min(1),
  tableId: z.string().min(1),
  updatedAt: z.string(),
})

const layoutPresetSchema: z.ZodType<LayoutPreset> = z.object({
  id: z.string().min(1),
  layout: z.enum(['balanced', 'graph', 'inspector', 'table']),
  page: z.enum(['artifacts', 'compare', 'constraints', 'graph', 'history', 'operations', 'reports', 'test-cases', 'workspace']),
  runName: z.string().min(1),
  updatedAt: z.string(),
})

const recentEntitySchema: z.ZodType<RecentEntity> = z.object({
  entityId: z.string().min(1),
  entityType: z.enum(['artifact', 'constraint', 'graph-edge', 'graph-sequence', 'invariant', 'operation', 'test-case']),
  href: z.string().min(1),
  label: z.string().min(1),
  runName: z.string().min(1),
  source: z.enum(['builder', 'compare', 'graph', 'operations', 'workspace']),
  updatedAt: z.string(),
})

const tablePowerPresetSchema: z.ZodType<TablePowerPreset> = z.object({
  columnVisibilityModel: z.record(z.string(), z.boolean()).catch({}),
  id: z.string().min(1),
  name: z.string().min(1),
  page: z.enum(['artifacts', 'compare', 'constraints', 'graph', 'history', 'operations', 'reports', 'test-cases', 'workspace']),
  runName: z.string().min(1),
  tableId: z.string().min(1),
  updatedAt: z.string(),
})

function collectionSchema<T extends z.ZodTypeAny>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema),
    version: z.literal(storageVersion),
  })
}

function readCollection<T>(key: string, itemSchema: z.ZodType<T>): T[] {
  if (typeof window === 'undefined') return []

  try {
    const rawValue = window.localStorage.getItem(key)
    if (!rawValue) return []
    return collectionSchema(itemSchema).parse(JSON.parse(rawValue)).items
  } catch {
    return []
  }
}

function writeCollection<T>(key: string, items: T[]) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(key, JSON.stringify({ items, version: storageVersion }))
}

function stablePart(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'item'
}

export function loadSavedViews() {
  return readCollection(apipilotSavedViewsStorageKey, savedViewSchema)
}

export function saveSavedViews(items: SavedView[]) {
  writeCollection(apipilotSavedViewsStorageKey, items)
}

export function loadBookmarks() {
  return readCollection(apipilotBookmarksStorageKey, bookmarkSchema)
}

export function saveBookmarks(items: WorkspaceBookmark[]) {
  writeCollection(apipilotBookmarksStorageKey, items)
}

export function loadWorkspaceNotes() {
  return readCollection(apipilotWorkspaceNotesStorageKey, noteSchema)
}

export function saveWorkspaceNotes(items: WorkspaceNote[]) {
  writeCollection(apipilotWorkspaceNotesStorageKey, items)
}

export function loadTableLayouts() {
  return readCollection(apipilotTableLayoutsStorageKey, tableLayoutSchema)
}

export function saveTableLayouts(items: TableLayout[]) {
  writeCollection(apipilotTableLayoutsStorageKey, items)
}

export function loadLayoutPresets() {
  return readCollection(apipilotLayoutPresetsStorageKey, layoutPresetSchema)
}

export function saveLayoutPresets(items: LayoutPreset[]) {
  writeCollection(apipilotLayoutPresetsStorageKey, items)
}

export function loadRecentEntities() {
  return readCollection(apipilotRecentEntitiesStorageKey, recentEntitySchema)
}

export function saveRecentEntities(items: RecentEntity[]) {
  writeCollection(apipilotRecentEntitiesStorageKey, items.slice(0, 24))
}

export function loadTablePowerPresets() {
  return readCollection(apipilotTablePowerPresetsStorageKey, tablePowerPresetSchema)
}

export function saveTablePowerPresets(items: TablePowerPreset[]) {
  writeCollection(apipilotTablePowerPresetsStorageKey, items)
}

export function savedViewId(runName: string, page: WorkspacePageId, name: string) {
  return `view:${stablePart(runName)}:${page}:${stablePart(name)}`
}

export function entityRecordId(runName: string, entityType: WorkspaceEntityType, entityId: string) {
  return `${stablePart(runName)}:${entityType}:${stablePart(entityId)}`
}

export function upsertSavedView(
  items: SavedView[],
  input: Omit<SavedView, 'createdAt' | 'id' | 'updatedAt'> & Partial<Pick<SavedView, 'id'>>,
  now = new Date().toISOString(),
) {
  const id = input.id ?? savedViewId(input.runName, input.page, input.name)
  const existing = items.find((item) => item.id === id)
  const next: SavedView = {
    ...input,
    createdAt: existing?.createdAt ?? now,
    id,
    updatedAt: now,
  }

  return [next, ...items.filter((item) => item.id !== id)]
}

export function upsertBookmark(
  items: WorkspaceBookmark[],
  input: Omit<WorkspaceBookmark, 'createdAt' | 'id'> & Partial<Pick<WorkspaceBookmark, 'id'>>,
  now = new Date().toISOString(),
) {
  const id = input.id ?? entityRecordId(input.runName, input.entityType, input.entityId)
  const existing = items.find((item) => item.id === id)
  const next: WorkspaceBookmark = {
    ...input,
    createdAt: existing?.createdAt ?? now,
    id,
  }

  return [next, ...items.filter((item) => item.id !== id)]
}

export function upsertWorkspaceNote(
  items: WorkspaceNote[],
  input: Omit<WorkspaceNote, 'createdAt' | 'id' | 'updatedAt'> & Partial<Pick<WorkspaceNote, 'id'>>,
  now = new Date().toISOString(),
) {
  const id = input.id ?? entityRecordId(input.runName, input.entityType, input.entityId)
  const existing = items.find((item) => item.id === id)
  const next: WorkspaceNote = {
    ...input,
    createdAt: existing?.createdAt ?? now,
    id,
    updatedAt: now,
  }

  return [next, ...items.filter((item) => item.id !== id)]
}

export function tableLayoutId(runName: string, page: WorkspacePageId, tableId: string) {
  return `table:${stablePart(runName)}:${page}:${stablePart(tableId)}`
}

export function layoutPresetId(runName: string, page: WorkspacePageId) {
  return `layout:${stablePart(runName)}:${page}`
}

export function tablePowerPresetId(runName: string, page: WorkspacePageId, tableId: string, name: string) {
  return `table-power:${stablePart(runName)}:${page}:${stablePart(tableId)}:${stablePart(name)}`
}

export function upsertTableLayout(
  items: TableLayout[],
  input: Omit<TableLayout, 'id' | 'updatedAt'> & Partial<Pick<TableLayout, 'id'>>,
  now = new Date().toISOString(),
) {
  const id = input.id ?? tableLayoutId(input.runName, input.page, input.tableId)
  const next: TableLayout = {
    ...input,
    id,
    updatedAt: now,
  }

  return [next, ...items.filter((item) => item.id !== id)]
}

export function upsertLayoutPreset(
  items: LayoutPreset[],
  input: Omit<LayoutPreset, 'id' | 'updatedAt'> & Partial<Pick<LayoutPreset, 'id'>>,
  now = new Date().toISOString(),
) {
  const id = input.id ?? layoutPresetId(input.runName, input.page)
  const next: LayoutPreset = {
    ...input,
    id,
    updatedAt: now,
  }

  return [next, ...items.filter((item) => item.id !== id)]
}

export function upsertRecentEntity(
  items: RecentEntity[],
  input: Omit<RecentEntity, 'updatedAt'>,
  now = new Date().toISOString(),
) {
  const next: RecentEntity = {
    ...input,
    updatedAt: now,
  }

  return [next, ...items.filter((item) =>
    !(item.runName === input.runName && item.entityType === input.entityType && item.entityId === input.entityId),
  )].slice(0, 24)
}

export function upsertTablePowerPreset(
  items: TablePowerPreset[],
  input: Omit<TablePowerPreset, 'id' | 'updatedAt'> & Partial<Pick<TablePowerPreset, 'id'>>,
  now = new Date().toISOString(),
) {
  const id = input.id ?? tablePowerPresetId(input.runName, input.page, input.tableId, input.name)
  const next: TablePowerPreset = {
    ...input,
    id,
    updatedAt: now,
  }

  return [next, ...items.filter((item) => item.id !== id)]
}
