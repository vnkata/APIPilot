const BODY_FIELD_PATTERN = /(^|[-_])body($|[-_])/i
const SENSITIVE_FIELD_PATTERN =
  /(^|[-_])(authorization|api[-_]?key|cookie|password|passwd|secret|session|token)($|[-_])/i
const REDACTED_VALUE = '<REDACTED>'

type RedactionStats = {
  omittedBodyFields: number
  redactedFields: number
}

export type ExportSnapshotInput = {
  data: unknown
  filters?: Record<string, unknown>
  includeBodies: boolean
  includeLocalContext?: boolean
  localContext?: unknown
  route: string
  selectedContext?: unknown
  title: string
}

function sanitizeForExportWithStats(value: unknown, includeBodies: boolean, stats: RedactionStats): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeForExportWithStats(item, includeBodies, stats))
  }

  if (!value || typeof value !== 'object') return value

  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>)
      .filter(([key]) => {
        const keep = includeBodies || !BODY_FIELD_PATTERN.test(key)
        if (!keep) stats.omittedBodyFields += 1
        return keep
      })
      .map(([key, item]) => [
        key,
        SENSITIVE_FIELD_PATTERN.test(key)
          ? (() => {
              stats.redactedFields += 1
              return REDACTED_VALUE
            })()
          : sanitizeForExportWithStats(item, includeBodies, stats),
      ]),
  )
}

export function sanitizeForExport(value: unknown, includeBodies: boolean): unknown {
  return sanitizeForExportWithStats(value, includeBodies, { omittedBodyFields: 0, redactedFields: 0 })
}

export function buildExportSnapshot({
  data,
  filters = {},
  includeBodies,
  includeLocalContext = false,
  localContext,
  route,
  selectedContext,
  title,
}: ExportSnapshotInput) {
  const stats: RedactionStats = { omittedBodyFields: 0, redactedFields: 0 }
  const sanitizedData = sanitizeForExportWithStats(data, includeBodies, stats)
  const sanitizedFilters = sanitizeForExportWithStats(filters, includeBodies, stats)
  const sanitizedLocalContext = includeLocalContext
    ? sanitizeForExportWithStats(localContext, includeBodies, stats)
    : undefined
  const sanitizedSelectedContext = selectedContext
    ? sanitizeForExportWithStats(selectedContext, includeBodies, stats)
    : undefined

  return {
    data: sanitizedData,
    exported_at: new Date().toISOString(),
    filters: sanitizedFilters,
    include_bodies: includeBodies,
    include_local_context: includeLocalContext,
    local_context: sanitizedLocalContext,
    redaction_summary: {
      omitted_body_fields: stats.omittedBodyFields,
      redacted_fields: stats.redactedFields,
    },
    route,
    selected_context: sanitizedSelectedContext,
    title,
  }
}

export function formatExportSnapshot(snapshot: unknown) {
  return JSON.stringify(snapshot, null, 2)
}
