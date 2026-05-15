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
const optionalBooleanFlag = z
  .preprocess((value) => {
    if (value === '' || value === null || value === undefined) return undefined
    if (value === true || value === 'true' || value === '1') return true
    if (value === false || value === 'false' || value === '0') return false
    return value
  }, z.boolean().optional())
  .catch(undefined)

export const operationsSearchSchema = z.object({
  groupBy: nullableString,
  hasConstraints: optionalBooleanFlag,
  hasFailures: optionalBooleanFlag,
  hasGraphEdges: optionalBooleanFlag,
  hasInvariants: optionalBooleanFlag,
  hasRequestBody: optionalBooleanFlag,
  httpMethod: nullableString,
  limit,
  offset,
  operationId: nullableString,
  operationKey: nullableString,
  q: nullableString,
  responseStatus: nullableString,
  sortBy: nullableString,
  sortOrder,
})

export const graphSearchSchema = z.object({
  edgeId: nullableString,
  edgeStatus: nullableString,
  evidenceSource: nullableString,
  fromNode: nullableString,
  fromOperationId: nullableString,
  groupBy: nullableString,
  graphTab: z.enum(['visual', 'edges', 'nodes', 'sequences']).catch('edges'),
  limit,
  nodeKind: nullableString,
  offset,
  operationId: nullableString,
  q: nullableString,
  sequenceId: nullableString,
  sequenceType: nullableString,
  sortBy: nullableString,
  sortOrder,
  targetOperationId: nullableString,
  toNode: nullableString,
  toOperationId: nullableString,
})

export const constraintsSearchSchema = z.object({
  agreementStatus: nullableString,
  assertionAvailable: optionalBooleanFlag,
  constraintId: nullableString,
  constraintKind: nullableString,
  constraintTab: z.enum(['explorer', 'static', 'dynamic', 'invariants']).catch('explorer'),
  correlationConfidence: nullableString,
  groupBy: nullableString,
  invariantId: nullableString,
  invariantKind: nullableString,
  invariantType: nullableString,
  limit,
  oracleReadiness: nullableString,
  offset,
  operationId: nullableString,
  propertyPath: nullableString,
  propertyPrefix: nullableString,
  q: nullableString,
  section: nullableString,
  sortBy: nullableString,
  sortOrder,
  source: nullableString,
  sourceType: nullableString,
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
