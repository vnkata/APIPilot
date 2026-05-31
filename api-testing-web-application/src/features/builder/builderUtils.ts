import type { ExecutionResponse } from '../../shared/api/generated/model'

export const activeExecutionStatuses = new Set(['queued', 'running', 'cancel_requested'])
export const terminalExecutionStatuses = new Set(['completed', 'failed', 'cancelled'])

export function isActiveExecution(status: string | undefined) {
  return Boolean(status && activeExecutionStatuses.has(status))
}

export function executionStatusColor(status: string): 'default' | 'error' | 'info' | 'success' | 'warning' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'cancelled') return 'default'
  if (status === 'cancel_requested') return 'warning'
  return 'info'
}

export function executionCanCancel(execution?: ExecutionResponse) {
  return isActiveExecution(execution?.status)
}

export function builderPath(path: string) {
  return `/builder${path.startsWith('/') ? path : `/${path}`}`
}

export function encodePathPart(value: string) {
  return encodeURIComponent(value)
}

export function isSensitiveHeaderName(name: string) {
  return /^(authorization|cookie|x-api-key|api-key|apikey)$/i.test(name.trim())
}

export function jsonPreview(value: unknown) {
  return JSON.stringify(value, null, 2)
}
