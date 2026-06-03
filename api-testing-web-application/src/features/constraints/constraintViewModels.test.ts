import { combinationEntries, constraintExplorerEntries, invariantExplorerEntries } from '../../test/fixtures'
import {
  buildCurrentPageConstraintMatrix,
  deriveCombinationReviewSignal,
  isCombinationEligibleForCounterExample,
  deriveConstraintLineage,
  parseAssertionSummary,
} from './constraintViewModels'

describe('constraint view models', () => {
  it('summarizes supported Postman assertions and safely falls back for custom assertions', () => {
    expect(parseAssertionSummary('pm.expect(input.limit).to.be.at.least(1)')).toMatchObject({
      kind: 'bounds',
      title: 'Minimum bound',
      subject: 'input.limit',
    })
    expect(parseAssertionSummary('pm.expect(return_url).to.match(/^https:\\/\\//)')).toMatchObject({
      kind: 'regex',
      title: 'Pattern match',
      subject: 'return_url',
    })
    expect(parseAssertionSummary('pm.expect(input_holidayId).to.eql(return_holiday_id)')).toMatchObject({
      kind: 'equality',
      title: 'Equality check',
      subject: 'input_holidayId',
    })
    expect(parseAssertionSummary('pm.expect(["A", "B"].includes(return_code)).to.be.true')).toMatchObject({
      kind: 'membership',
      title: 'Allowed values',
      subject: 'return_code',
    })
    expect(parseAssertionSummary('pm.expect(customAssertion()).to.be.true')).toMatchObject({
      kind: 'custom',
      title: 'Custom assertion',
    })
  })

  it('derives conservative static/dynamic/combined lineage labels', () => {
    const lineage = deriveConstraintLineage(constraintExplorerEntries.items[0])

    expect(lineage.signals.map((signal) => signal.label)).toEqual(
      expect.arrayContaining(['Static present', 'Dynamic present', 'Combined expression']),
    )
    expect(lineage.textMatches).toEqual(
      expect.arrayContaining(['Text matches static expression', 'Text matches combined expression']),
    )
  })

  it('builds current-page matrices for source, kind, and readiness', () => {
    expect(
      buildCurrentPageConstraintMatrix({
        constraints: constraintExplorerEntries.items,
        invariants: invariantExplorerEntries.items,
        matrixBy: 'source',
      }).cells,
    ).toEqual(expect.arrayContaining([expect.objectContaining({ count: 1, label: 'combined' })]))

    expect(
      buildCurrentPageConstraintMatrix({
        constraints: constraintExplorerEntries.items,
        invariants: invariantExplorerEntries.items,
        matrixBy: 'kind',
      }).cells,
    ).toEqual(expect.arrayContaining([expect.objectContaining({ count: 1, label: 'bounds' })]))

    expect(
      buildCurrentPageConstraintMatrix({
        constraints: constraintExplorerEntries.items,
        invariants: invariantExplorerEntries.items,
        matrixBy: 'readiness',
      }).cells,
    ).toEqual(expect.arrayContaining([expect.objectContaining({ count: 1, label: 'verified_runtime_oracle' })]))
  })

  it('derives combination review priority from relation, status, and manual decisions', () => {
    expect(deriveCombinationReviewSignal({
      ...combinationEntries.items[0],
      relation: 'DISJOINT',
      status: 'CONFLICT',
    })).toMatchObject({
      label: 'Conflict needs decision',
      priority: 'conflict',
      recommendedNextAction: 'Open review workspace and decide whether to reject the relation or keep no final constraint.',
      tone: 'danger',
    })

    expect(deriveCombinationReviewSignal({
      ...combinationEntries.items[0],
      relation: 'DYNAMIC_STRONGER',
      resolved: false,
      status: 'UNRESOLVED',
    })).toMatchObject({
      label: 'Needs review',
      priority: 'needs_review',
      tone: 'warning',
    })

    expect(deriveCombinationReviewSignal({
      ...combinationEntries.items[0],
      has_manual_decision: true,
      manual_decision: 'ACCEPT_STATIC',
      review_state: 'FINAL_CONFIRMED',
    })).toMatchObject({
      label: 'Human decision',
      priority: 'human_decision',
      tone: 'success',
    })

    expect(deriveCombinationReviewSignal({
      ...combinationEntries.items[0],
      relation: null,
      status: 'UNIQUE_STATIC',
    })).toMatchObject({
      label: 'Unique constraint',
      priority: 'unique',
      tone: 'info',
    })
  })

  it('limits counter-example generation eligibility to unresolved paired relations', () => {
    expect(isCombinationEligibleForCounterExample({
      ...combinationEntries.items[0],
      relation: 'PARTIAL_OVERLAP',
      resolved: false,
      status: 'UNRESOLVED',
    })).toBe(true)

    expect(isCombinationEligibleForCounterExample({
      ...combinationEntries.items[0],
      relation: 'EQUIVALENT',
      resolved: true,
      status: 'RESOLVED',
    })).toBe(false)

    expect(isCombinationEligibleForCounterExample({
      ...combinationEntries.items[0],
      has_manual_decision: true,
      manual_decision: 'ACCEPT_STATIC',
      relation: 'UNKNOWN',
      review_state: 'FINAL_CONFIRMED',
      resolved: false,
      status: 'UNRESOLVED',
    })).toBe(false)
  })
})
