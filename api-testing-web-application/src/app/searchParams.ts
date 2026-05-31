import { z } from 'zod'

const nullableString = z
  .preprocess((value) => (value === '' || value === null ? undefined : value), z.string().optional())
  .catch(undefined)

const limit = z.coerce.number().int().min(1).max(200).catch(25)
const offset = z.coerce.number().int().min(0).catch(0)
const sortOrder = z.enum(['asc', 'desc']).catch('asc')
const overviewView = z.enum(['classic', 'command']).catch('command')
const operationsView = z.enum(['table', 'canvas', 'cards']).catch('table')
const graphView = z.enum(['explorer', 'journey', 'spatial']).catch('explorer')
const focusMode = z.enum(['all', 'neighborhood', 'path']).catch('all')
const motionMode = z.enum(['auto', 'reduced', 'off']).catch('auto')
const constraintsView = z.enum(['workbench', 'table', 'matrix']).catch('workbench')
const constraintDetailView = z.enum(['readable', 'raw']).catch('readable')
const matrixBy = z.enum(['source', 'kind', 'readiness']).catch('source')
const artifactsView = z.enum(['classic', 'workbench']).catch('workbench')
const artifactMode = z.enum(['compare', 'raw', 'summary']).optional().catch(undefined)
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

export const runOverviewSearchSchema = z.object({
  overviewView,
})

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
  operationsView,
  q: nullableString,
  responseStatus: nullableString,
  sortBy: nullableString,
  sortOrder,
})

export const graphSearchSchema = z.object({
  edgeId: nullableString,
  edgeStatus: nullableString,
  evidenceSource: nullableString,
  focusMode,
  fromNode: nullableString,
  fromOperationId: nullableString,
  groupBy: nullableString,
  graphTab: z.enum(['visual', 'edges', 'nodes', 'sequences']).catch('edges'),
  graphView,
  limit,
  nodeKind: nullableString,
  offset,
  operationId: nullableString,
  q: nullableString,
  motionMode,
  selectedPath: nullableString,
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
  constraintDetailView,
  constraintId: nullableString,
  constraintKind: nullableString,
  constraintTab: z.enum(['explorer', 'static', 'dynamic', 'invariants']).catch('explorer'),
  constraintsView,
  correlationConfidence: nullableString,
  groupBy: nullableString,
  invariantId: nullableString,
  invariantKind: nullableString,
  invariantType: nullableString,
  limit,
  matrixBy,
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

export const artifactsSearchSchema = z
  .object({
    artifactId: nullableString,
    artifactMode,
    artifactsView,
    compare: booleanFlag,
    raw: booleanFlag,
  })
  .transform((search) => ({
    ...search,
    artifactMode: search.artifactMode ?? (search.compare ? 'compare' : search.raw ? 'raw' : 'summary'),
  }))

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

export const compareSearchSchema = z.object({
  artifactId: nullableString,
  leftRun: nullableString,
  raw: booleanFlag,
  rightRun: nullableString,
})
