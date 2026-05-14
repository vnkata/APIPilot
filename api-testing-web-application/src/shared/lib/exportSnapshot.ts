const BODY_FIELD_PATTERN = /(^|_)(body)($|_)/i

export type ExportSnapshotInput = {
  data: unknown
  filters?: Record<string, unknown>
  includeBodies: boolean
  route: string
  selectedContext?: unknown
  title: string
}

function sanitizeForExport(value: unknown, includeBodies: boolean): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeForExport(item, includeBodies))
  }

  if (!value || typeof value !== 'object') return value

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([key]) => includeBodies || !BODY_FIELD_PATTERN.test(key))
      .map(([key, item]) => [key, sanitizeForExport(item, includeBodies)]),
  )
}

export function buildExportSnapshot({
  data,
  filters = {},
  includeBodies,
  route,
  selectedContext,
  title,
}: ExportSnapshotInput) {
  return {
    data: sanitizeForExport(data, includeBodies),
    exported_at: new Date().toISOString(),
    filters: sanitizeForExport(filters, includeBodies),
    include_bodies: includeBodies,
    route,
    selected_context: selectedContext ? sanitizeForExport(selectedContext, includeBodies) : undefined,
    title,
  }
}

export function formatExportSnapshot(snapshot: unknown) {
  return JSON.stringify(snapshot, null, 2)
}
