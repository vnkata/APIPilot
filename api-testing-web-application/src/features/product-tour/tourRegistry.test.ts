import { describe, expect, it } from 'vitest'

import { availableTourIds, loadTourDefinition, tourMetas } from './tourRegistry'

describe('tourRegistry', () => {
  it('maps each major route to the global tour and one contextual page tour', () => {
    expect(availableTourIds('/runs')).toEqual(['app-shell', 'runs'])
    expect(availableTourIds('/runs/Run%20A')).toEqual(['app-shell', 'overview'])
    expect(availableTourIds('/runs/Run%20A/operations')).toEqual(['app-shell', 'operations'])
    expect(availableTourIds('/runs/Run%20A/graph')).toEqual(['app-shell', 'graph'])
    expect(availableTourIds('/runs/Run%20A/constraints')).toEqual(['app-shell', 'constraints'])
    expect(availableTourIds('/runs/Run%20A/artifacts')).toEqual(['app-shell', 'artifacts'])
    expect(availableTourIds('/runs/Run%20A/reports')).toEqual(['app-shell', 'reports'])
    expect(availableTourIds('/runs/Run%20A/test-cases')).toEqual(['app-shell', 'test-cases'])
    expect(availableTourIds('/runs/Run%20A/history')).toEqual(['app-shell', 'history'])
  })

  it('loads definitions with unique ids and stable step anchors', async () => {
    const tourIds = tourMetas.map((meta) => meta.id)
    expect(new Set(tourIds).size).toBe(tourIds.length)

    const definitions = await Promise.all(tourIds.map((tourId) => loadTourDefinition(tourId)))
    definitions.forEach((definition) => {
      expect(definition.version).toBe(1)
      expect(definition.roles).toEqual(['qa-qc'])
      expect(definition.steps.length).toBeGreaterThan(0)
      expect(new Set(definition.steps.map((step) => step.id)).size).toBe(definition.steps.length)
      definition.steps.forEach((step) => {
        expect(step.anchorId).toMatch(/^[a-z-]+$/)
      })
    })
  })
})
