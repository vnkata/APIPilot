import { constraintExplorerEntries, invariantExplorerEntries } from '../../test/fixtures'
import {
  buildCurrentPageConstraintMatrix,
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
})
