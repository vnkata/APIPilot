import axios from 'axios'

export type NormalizedApiError = {
  code: string
  message: string
  status?: number
  title: string
}

type BackendErrorPayload = {
  error?: {
    code?: unknown
    message?: unknown
  }
  detail?: unknown
}

type ValidationDetail = {
  loc?: unknown
  msg?: unknown
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function titleFromCode(code: string, status?: number) {
  if (code === 'invalid_request') return 'Invalid request'
  if (code === 'not_found') return 'Not found'
  if (code === 'validation_error') return 'Validation error'
  if (status === 404) return 'Not found'
  if (status === 400) return 'Invalid request'
  if (status === 422) return 'Validation error'
  if (status && status >= 500) return 'Backend unavailable'
  return 'Request failed'
}

function validationMessage(detail: unknown) {
  if (!Array.isArray(detail)) return undefined

  return detail
    .slice(0, 3)
    .map((entry: ValidationDetail) => {
      const location = Array.isArray(entry.loc) ? entry.loc.join('.') : undefined
      const message = typeof entry.msg === 'string' ? entry.msg : 'Invalid value'
      return location ? `${location}: ${message}` : message
    })
    .join('; ')
}

export function normalizeApiError(error: unknown): NormalizedApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const payload = isRecord(error.response?.data) ? (error.response.data as BackendErrorPayload) : undefined
    const backendError = isRecord(payload?.error) ? payload.error : undefined

    if (typeof backendError?.code === 'string' && typeof backendError.message === 'string') {
      return {
        code: backendError.code,
        message: backendError.message,
        status,
        title: titleFromCode(backendError.code, status),
      }
    }

    const formattedValidation = validationMessage(payload?.detail)
    if (formattedValidation) {
      return {
        code: 'validation_error',
        message: formattedValidation,
        status,
        title: titleFromCode('validation_error', status),
      }
    }

    if (!error.response) {
      return {
        code: 'network_error',
        message: 'Cannot reach the APIPilot backend. Check the local server and API base URL.',
        title: 'Network error',
      }
    }

    return {
      code: 'http_error',
      message: error.message || 'The backend request failed.',
      status,
      title: titleFromCode('http_error', status),
    }
  }

  if (error instanceof Error) {
    return {
      code: 'client_error',
      message: error.message,
      title: 'Client error',
    }
  }

  return {
    code: 'unknown_error',
    message: 'An unknown error occurred.',
    title: 'Unknown error',
  }
}
