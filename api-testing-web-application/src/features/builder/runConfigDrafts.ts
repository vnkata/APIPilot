import { z } from 'zod'

export const runConfigDraftsStorageKey = 'apipilot.runConfigDrafts.v1'

const storageVersion = 1

const persistedDraftSchema = z.object({
  asyncMode: z.boolean().optional(),
  configName: z.string().optional(),
  constraintMining: z.boolean().optional(),
  embeddingModel: z.string().optional(),
  embeddingProvider: z.string().optional(),
  headerMutationRatio: z.number().min(0).max(1).optional(),
  liveApi: z.boolean().optional(),
  llmModel: z.string().optional(),
  llmProvider: z.string().optional(),
  mutationRatio: z.number().min(0).max(1).optional(),
  numGenerations: z.number().int().min(1).optional(),
  numTestCases: z.number().int().min(1).optional(),
  requestBudget: z.number().int().min(1).optional(),
  specId: z.string().optional(),
  timeoutSeconds: z.number().int().min(1).optional(),
})

const storedValueSchema = z.object({
  draft: persistedDraftSchema,
  version: z.literal(storageVersion),
})

export type PersistedRunConfigDraft = z.infer<typeof persistedDraftSchema>

export type RunConfigDraftInput = PersistedRunConfigDraft & {
  baseUrl?: string
  headerDrafts?: Array<{
    name: string
    refName?: string
    type: 'env' | 'plain'
    value?: string
  }>
}

function sanitizeDraft(input: RunConfigDraftInput): PersistedRunConfigDraft {
  return {
    asyncMode: input.asyncMode,
    configName: input.configName,
    constraintMining: input.constraintMining,
    embeddingModel: input.embeddingModel,
    embeddingProvider: input.embeddingProvider,
    headerMutationRatio: input.headerMutationRatio,
    liveApi: input.liveApi,
    llmModel: input.llmModel,
    llmProvider: input.llmProvider,
    mutationRatio: input.mutationRatio,
    numGenerations: input.numGenerations,
    numTestCases: input.numTestCases,
    requestBudget: input.requestBudget,
    specId: input.specId,
    timeoutSeconds: input.timeoutSeconds,
  }
}

export function loadRunConfigDraft(): PersistedRunConfigDraft | undefined {
  if (typeof window === 'undefined') return undefined

  try {
    const rawValue = window.localStorage.getItem(runConfigDraftsStorageKey)
    if (!rawValue) return undefined
    return storedValueSchema.parse(JSON.parse(rawValue)).draft
  } catch {
    return undefined
  }
}

export function saveRunConfigDraft(input: RunConfigDraftInput) {
  if (typeof window === 'undefined') return

  const draft = sanitizeDraft(input)
  window.localStorage.setItem(runConfigDraftsStorageKey, JSON.stringify({ draft, version: storageVersion }))
}

export function clearRunConfigDraft() {
  if (typeof window === 'undefined') return
  window.localStorage.removeItem(runConfigDraftsStorageKey)
}
