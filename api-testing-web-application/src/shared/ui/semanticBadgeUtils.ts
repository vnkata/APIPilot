import type { StatusCodeToken } from '../../theme/tokens'

export function getStatusCodeToken(statusCode: number | string | null | undefined): StatusCodeToken {
  const numeric = Number(statusCode)
  if (!Number.isFinite(numeric)) return 'unknown'
  if (numeric >= 200 && numeric < 300) return 'success'
  if (numeric >= 300 && numeric < 400) return 'redirect'
  if (numeric >= 400 && numeric < 500) return 'clientError'
  if (numeric >= 500 && numeric < 600) return 'serverError'
  return 'unknown'
}
