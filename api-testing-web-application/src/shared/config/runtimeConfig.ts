import { z } from 'zod'

const DEFAULT_API_BASE_URL = 'http://localhost:8000'
const DEFAULT_API_TIMEOUT_MS = 15_000

const runtimeEnvSchema = z.object({
  VITE_API_BASE_URL: z
    .string()
    .trim()
    .url()
    .optional()
    .catch(DEFAULT_API_BASE_URL),
  VITE_API_TIMEOUT_MS: z.coerce
    .number()
    .int()
    .min(1_000)
    .max(120_000)
    .optional()
    .catch(DEFAULT_API_TIMEOUT_MS),
})

const parsedRuntimeEnv = runtimeEnvSchema.parse(import.meta.env)

export const runtimeConfig = {
  apiBaseUrl: parsedRuntimeEnv.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
  apiTimeoutMs: parsedRuntimeEnv.VITE_API_TIMEOUT_MS ?? DEFAULT_API_TIMEOUT_MS,
} as const

export function getSafeRuntimeDiagnostics() {
  return {
    apiBaseUrl: runtimeConfig.apiBaseUrl,
    apiTimeoutMs: runtimeConfig.apiTimeoutMs,
  }
}
