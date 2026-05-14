import { z } from 'zod'

const nullableString = z
  .preprocess((value) => (value === '' || value === null ? undefined : value), z.string().optional())
  .catch(undefined)

const limit = z.coerce.number().int().min(1).max(200).catch(25)
const offset = z.coerce.number().int().min(0).catch(0)
const sortOrder = z.enum(['asc', 'desc']).catch('asc')
const booleanFlag = z
  .preprocess((value) => value === true || value === 'true' || value === '1', z.boolean())
  .catch(false)

export const graphSearchSchema = z.object({
  edgeId: nullableString,
  fromNode: nullableString,
  groupBy: nullableString,
  limit,
  offset,
  operationId: nullableString,
  q: nullableString,
  sortBy: nullableString,
  sortOrder,
  toNode: nullableString,
})

export const constraintsSearchSchema = z.object({
  constraintTab: z.enum(['static', 'dynamic', 'invariants']).catch('static'),
  groupBy: nullableString,
  invariantType: nullableString,
  limit,
  offset,
  operationId: nullableString,
  q: nullableString,
  section: nullableString,
  sortBy: nullableString,
  sortOrder,
})

export const artifactsSearchSchema = z.object({
  artifactId: nullableString,
  compare: booleanFlag,
  raw: booleanFlag,
})

export const reportsSearchSchema = z.object({
  groupBy: nullableString,
  limit,
  offset,
  operationId: nullableString,
  q: nullableString,
  sortBy: nullableString,
  sortOrder,
  statusCode: nullableString,
})

export const testCasesSearchSchema = z.object({
  includeBody: booleanFlag,
  limit,
  offset,
  operationId: nullableString,
  statusCode: z.coerce.number().int().min(100).max(599).optional().catch(undefined),
  testCaseId: nullableString,
})

export const historySearchSchema = z.object({
  entryId: nullableString,
  includeBody: booleanFlag,
  limit,
  offset,
  sessionId: nullableString,
})
