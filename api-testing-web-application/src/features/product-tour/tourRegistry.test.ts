import { describe, expect, it } from 'vitest'

import { availableTourIds, loadTourDefinition, tourMetas } from './tourRegistry'

describe('tourRegistry', () => {
  it('maps each major route to the global tour and contextual page tours', () => {
    expect(availableTourIds('/runs')).toEqual(['app-shell', 'runs'])
    expect(availableTourIds('/runs/Run%20A')).toEqual(['app-shell', 'overview'])
    expect(availableTourIds('/runs/Run%20A/operations')).toEqual(['app-shell', 'operations'])
    expect(availableTourIds('/runs/Run%20A/graph')).toEqual(['app-shell', 'graph'])
    expect(availableTourIds('/runs/Run%20A/workspace')).toEqual(['app-shell', 'workspace'])
    expect(availableTourIds('/runs/Run%20A/constraints')).toEqual([
      'app-shell',
      'constraints-fundamentals',
      'constraints-workbench',
      'constraints-explorer',
    ])
    expect(availableTourIds('/runs/Run%20A/artifacts')).toEqual(['app-shell', 'artifacts'])
    expect(availableTourIds('/runs/Run%20A/reports')).toEqual(['app-shell', 'reports'])
    expect(availableTourIds('/runs/Run%20A/test-cases')).toEqual(['app-shell', 'test-cases'])
    expect(availableTourIds('/runs/Run%20A/history')).toEqual(['app-shell', 'history'])
    expect(availableTourIds('/builder/specs')).toEqual(['app-shell', 'builder-specs'])
    expect(availableTourIds('/builder/specs/spec-items')).toEqual(['app-shell', 'builder-specs'])
    expect(availableTourIds('/builder/run-configs/new')).toEqual(['app-shell', 'builder-run-config'])
    expect(availableTourIds('/builder/executions')).toEqual(['app-shell', 'builder-executions'])
    expect(availableTourIds('/builder/executions/exec-items')).toEqual(['app-shell', 'builder-execution-detail'])
    expect(availableTourIds('/compare')).toEqual(['app-shell', 'compare'])
  })

  it('loads rich definitions with unique ids, stable step anchors, and meaningful depth', async () => {
    const tourIds = tourMetas.map((meta) => meta.id)
    expect(new Set(tourIds).size).toBe(tourIds.length)

    const definitions = await Promise.all(tourIds.map((tourId) => loadTourDefinition(tourId)))
    definitions.forEach((definition) => {
      expect(definition.version).toBeGreaterThanOrEqual(1)
      expect(definition.roles).toEqual(['qa-qc'])
      expect(definition.steps.length).toBeGreaterThan(0)
      expect(new Set(definition.steps.map((step) => step.id)).size).toBe(definition.steps.length)
      definition.steps.forEach((step) => {
        expect(step.anchorId).toMatch(/^[a-z-]+$/)
      })
    })
    expect(definitions.find((definition) => definition.id === 'constraints-fundamentals')?.steps.length).toBeGreaterThanOrEqual(7)
    expect(definitions.find((definition) => definition.id === 'builder-run-config')?.steps.length).toBeGreaterThanOrEqual(7)
    expect(definitions.some((definition) => definition.steps.some((step) => step.bullets?.length))).toBe(true)
    expect(definitions.some((definition) => definition.steps.some((step) => step.whyItMatters))).toBe(true)
    expect(definitions.some((definition) => definition.steps.some((step) => step.domainTerm))).toBe(true)
  })
})
