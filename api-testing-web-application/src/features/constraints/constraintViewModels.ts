import type {
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
} from '../../shared/api/generated/model'

export type AssertionSummaryKind = 'bounds' | 'custom' | 'equality' | 'membership' | 'missing' | 'regex'

export type AssertionSummary = {
  code?: string | null
  description: string
  expectation?: string
  kind: AssertionSummaryKind
  subject?: string
  title: string
}

export type LineageSignal = {
  description?: string
  label: string
  tone: 'danger' | 'neutral' | 'success' | 'warning'
}

export type ConstraintLineage = {
  signals: LineageSignal[]
  textMatches: string[]
}

export type MatrixBy = 'kind' | 'readiness' | 'source'

export type CombinationReviewPriority = 'conflict' | 'human_decision' | 'needs_review' | 'resolved' | 'unique' | 'watch'

export type CombinationTone = 'danger' | 'info' | 'neutral' | 'success' | 'warning'

export type CombinationReviewSignal = {
  description: string
  label: string
  priority: CombinationReviewPriority
  rawValues: string[]
  recommendedNextAction: string
  tone: CombinationTone
}

export type CombinationReviewFields = {
  decision_source?: string | null
  has_manual_decision?: boolean | null
  manual_decision?: string | null
  relation?: string | null
  resolved?: boolean
  review_state?: string | null
  status?: string | null
}

export type MatrixCell = {
  count: number
  filter: Record<string, string | undefined>
  label: string
}

export type CurrentPageConstraintMatrix = {
  cells: MatrixCell[]
  description: string
  title: string
}

function normalizeExpression(value: string | null | undefined) {
  return value?.trim().replace(/\s+/g, ' ')
}

function stripQuotes(value: string) {
  return value.trim().replace(/^['"]|['"]$/g, '')
}

export function parseAssertionSummary(assertion: string | null | undefined): AssertionSummary {
  const originalCode = assertion?.trim()
  const code = originalCode?.replace(/;+$/, '')
  if (!originalCode || !code) {
    return {
      code: originalCode,
      description: 'No executable assertion is attached to this signal.',
      kind: 'missing',
      title: 'No assertion',
    }
  }

  const boundsMatch = code.match(/^pm\.expect\(([^)]+)\)\.to\.be\.at\.least\((.+)\)$/)
  if (boundsMatch) {
    return {
      code: originalCode,
      description: `Expect ${boundsMatch[1]} to be at least ${boundsMatch[2]}.`,
      expectation: boundsMatch[2],
      kind: 'bounds',
      subject: boundsMatch[1],
      title: 'Minimum bound',
    }
  }

  const regexMatch = code.match(/^pm\.expect\(([^)]+)\)\.to\.match\((\/.*\/[a-z]*)\)$/)
  if (regexMatch) {
    return {
      code: originalCode,
      description: `Expect ${regexMatch[1]} to match a regular expression.`,
      expectation: regexMatch[2],
      kind: 'regex',
      subject: regexMatch[1],
      title: 'Pattern match',
    }
  }

  const equalityMatch = code.match(/^pm\.expect\(([^)]+)\)\.to\.eql\((.+)\)$/)
  if (equalityMatch) {
    return {
      code: originalCode,
      description: `Expect ${equalityMatch[1]} to equal ${equalityMatch[2]}.`,
      expectation: equalityMatch[2],
      kind: 'equality',
      subject: equalityMatch[1],
      title: 'Equality check',
    }
  }

  const membershipMatch = code.match(/^pm\.expect\((\[.*\])\.includes\(([^)]+)\)\)\.to\.be\.true$/)
  if (membershipMatch) {
    return {
      code: originalCode,
      description: `Expect ${membershipMatch[2]} to be included in ${membershipMatch[1]}.`,
      expectation: membershipMatch[1],
      kind: 'membership',
      subject: membershipMatch[2],
      title: 'Allowed values',
    }
  }

  const includesMatch = code.match(/^pm\.expect\(([^)]+)\)\.to\.be\.oneOf\((\[.*\])\)$/)
  if (includesMatch) {
    return {
      code: originalCode,
      description: `Expect ${includesMatch[1]} to be one of ${includesMatch[2]}.`,
      expectation: includesMatch[2],
      kind: 'membership',
      subject: includesMatch[1],
      title: 'Allowed values',
    }
  }

  return {
    code: originalCode,
    description: 'This assertion uses a custom pattern. Review the code before treating it as a readable oracle.',
    kind: 'custom',
    title: 'Custom assertion',
  }
}

export function deriveConstraintLineage(row: ConstraintExplorerEntryResponse): ConstraintLineage {
  const expression = normalizeExpression(row.expression)
  const staticExpression = normalizeExpression(row.static_expression)
  const dynamicExpression = normalizeExpression(row.dynamic_expression)
  const combinedExpression = normalizeExpression(row.combined_expression)
  const textMatches: string[] = []

  if (expression && staticExpression && expression === staticExpression) {
    textMatches.push('Text matches static expression')
  }
  if (expression && dynamicExpression && expression === dynamicExpression) {
    textMatches.push('Text matches dynamic expression')
  }
  if (expression && combinedExpression && expression === combinedExpression) {
    textMatches.push('Text matches combined expression')
  }

  return {
    signals: [
      {
        description: row.static_expression ?? 'No static expression was found for this property path.',
        label: row.has_static ? 'Static present' : 'Static missing',
        tone: row.has_static ? 'success' : 'neutral',
      },
      {
        description: row.dynamic_expression ?? 'No dynamic expression was found for this property path.',
        label: row.has_dynamic ? 'Dynamic present' : 'Dynamic missing',
        tone: row.has_dynamic ? 'success' : 'neutral',
      },
      {
        description: row.combined_expression ?? 'No combined expression is attached to this row.',
        label: row.combined_expression ? 'Combined expression' : 'Combined missing',
        tone: row.combined_expression ? 'success' : 'warning',
      },
      {
        description: row.source_type ? `Raw provenance: ${row.source_type}` : undefined,
        label: `Agreement: ${row.agreement_status}`,
        tone: row.agreement_status === 'both_present' ? 'success' : 'warning',
      },
    ],
    textMatches,
  }
}

function countBy(items: string[]) {
  const counts = new Map<string, number>()
  for (const item of items) counts.set(item, (counts.get(item) ?? 0) + 1)
  return Array.from(counts.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([label, count]) => ({ count, label }))
}

const COUNTER_EXAMPLE_RELATIONS = new Set(['STATIC_STRONGER', 'DYNAMIC_STRONGER', 'PARTIAL_OVERLAP', 'DISJOINT', 'UNKNOWN'])

function hasHumanDecision(row: CombinationReviewFields) {
  return Boolean(row.has_manual_decision || row.manual_decision || row.decision_source || row.review_state === 'FINAL_CONFIRMED')
}

export function isCombinationEligibleForCounterExample(
  row: CombinationReviewFields,
) {
  return Boolean(row.relation && COUNTER_EXAMPLE_RELATIONS.has(row.relation) && !hasHumanDecision(row))
}

export function deriveCombinationReviewSignal(
  row: CombinationReviewFields,
): CombinationReviewSignal {
  const rawValues = [row.relation, row.status, row.review_state, row.manual_decision, row.decision_source].filter(Boolean) as string[]

  if (hasHumanDecision(row)) {
    return {
      description: 'A reviewer has recorded a decision for this combination.',
      label: 'Human decision',
      priority: 'human_decision',
      rawValues,
      recommendedNextAction: 'Review the human decision or reopen if more evidence is needed.',
      tone: 'success',
    }
  }

  if (row.relation === 'DISJOINT' || row.status === 'CONFLICT') {
    return {
      description: 'Static and dynamic constraints appear incompatible.',
      label: 'Conflict needs decision',
      priority: 'conflict',
      rawValues,
      recommendedNextAction: 'Open review workspace and decide whether to reject the relation or keep no final constraint.',
      tone: 'danger',
    }
  }

  if (
    row.relation === 'STATIC_STRONGER'
    || row.relation === 'DYNAMIC_STRONGER'
    || row.relation === 'PARTIAL_OVERLAP'
    || row.relation === 'UNKNOWN'
    || row.status === 'UNRESOLVED'
  ) {
    return {
      description: 'This combination needs human review before it should become a final constraint.',
      label: 'Needs review',
      priority: 'needs_review',
      rawValues,
      recommendedNextAction: 'Generate or inspect draft cases, then approve evidence and finalize a human decision.',
      tone: 'warning',
    }
  }

  if (row.status === 'UNIQUE_STATIC' || row.status === 'UNIQUE_DYNAMIC') {
    return {
      description: 'Only one side produced a constraint for this property.',
      label: 'Unique constraint',
      priority: 'unique',
      rawValues,
      recommendedNextAction: 'Inspect the source constraint if this property matters to the test oracle.',
      tone: 'info',
    }
  }

  if (row.resolved || row.relation === 'EQUIVALENT' || row.status === 'RESOLVED') {
    return {
      description: 'This relation has a final constraint from the combiner.',
      label: 'Resolved',
      priority: 'resolved',
      rawValues,
      recommendedNextAction: 'Inspect the final constraint or leave it as-is.',
      tone: 'success',
    }
  }

  return {
    description: 'This combination has no urgent review signal.',
    label: 'Watch',
    priority: 'watch',
    rawValues,
    recommendedNextAction: 'Open detail if the operation or property is important.',
    tone: 'neutral',
  }
}

export function buildCurrentPageConstraintMatrix({
  constraints,
  invariants,
  matrixBy,
}: {
  constraints: ConstraintExplorerEntryResponse[]
  invariants: InvariantExplorerEntryResponse[]
  matrixBy: MatrixBy
}): CurrentPageConstraintMatrix {
  if (matrixBy === 'kind') {
    return {
      cells: countBy(constraints.map((row) => row.constraint_kind)).map((cell) => ({
        ...cell,
        filter: { constraintKind: cell.label },
      })),
      description: 'Current page by constraint kind. Counts use loaded rows only.',
      title: 'Current page by kind',
    }
  }

  if (matrixBy === 'readiness') {
    return {
      cells: countBy(invariants.map((row) => row.oracle_readiness)).map((cell) => ({
        ...cell,
        filter: { oracleReadiness: cell.label },
      })),
      description: 'Current page by raw invariant oracle readiness. Counts use loaded rows only.',
      title: 'Current page by readiness',
    }
  }

  return {
    cells: countBy(constraints.map((row) => row.source)).map((cell) => ({
      ...cell,
      filter: { source: cell.label },
    })),
    description: 'Current page by constraint source. Counts use loaded rows only.',
    title: 'Current page by source',
  }
}

export function readableIdentifier(value: string | null | undefined) {
  if (!value) return 'Not available'
  return stripQuotes(value)
}
