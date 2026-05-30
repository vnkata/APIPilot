import ClearAllIcon from '@mui/icons-material/ClearAll'
import { Button, Chip, Stack, Typography } from '@mui/material'

import { replaceSearchParams } from '../../../shared/lib/navigation'
import { Panel } from '../../../shared/ui/Panel'
import type { ConstraintsPageSearch } from '../ConstraintsPage'

type ConstraintAppliedFiltersBarProps = {
  search: ConstraintsPageSearch
}

type AppliedFilter = {
  key: keyof ConstraintsPageSearch
  label: string
  value: boolean | number | string | undefined
}

const clearableKeys: Array<keyof ConstraintsPageSearch> = [
  'agreementStatus',
  'assertionAvailable',
  'constraintKind',
  'correlationConfidence',
  'groupBy',
  'invariantKind',
  'invariantType',
  'operationId',
  'oracleReadiness',
  'propertyPath',
  'propertyPrefix',
  'q',
  'section',
  'source',
  'sourceType',
]

function readableValue(value: boolean | number | string | undefined) {
  if (typeof value === 'boolean') return value ? 'Available' : 'Missing'
  return String(value)
}

function activeFilters(search: ConstraintsPageSearch): AppliedFilter[] {
  const filters: AppliedFilter[] = [
    { key: 'q', label: 'Search', value: search.q },
    { key: 'operationId', label: 'Operation', value: search.operationId },
    { key: 'section', label: 'Section', value: search.section },
    { key: 'source', label: 'Source', value: search.source },
    { key: 'constraintKind', label: 'Kind', value: search.constraintKind },
    { key: 'agreementStatus', label: 'Agreement', value: search.agreementStatus },
    { key: 'assertionAvailable', label: 'Assertion', value: search.assertionAvailable },
    { key: 'invariantKind', label: 'Invariant kind', value: search.invariantKind },
    { key: 'invariantType', label: 'Invariant type', value: search.invariantType },
    { key: 'oracleReadiness', label: 'Readiness', value: search.oracleReadiness },
    { key: 'correlationConfidence', label: 'Correlation', value: search.correlationConfidence },
    { key: 'propertyPath', label: 'Property', value: search.propertyPath },
    { key: 'propertyPrefix', label: 'Property prefix', value: search.propertyPrefix },
    { key: 'sourceType', label: 'Source type', value: search.sourceType },
    { key: 'groupBy', label: 'Group', value: search.groupBy },
  ]

  return filters.filter((filter) => filter.value !== undefined && filter.value !== '')
}

export function ConstraintAppliedFiltersBar({ search }: ConstraintAppliedFiltersBarProps) {
  const filters = activeFilters(search)
  const visibleFilters = filters.slice(0, 6)
  const hiddenCount = Math.max(filters.length - visibleFilters.length, 0)

  if (filters.length === 0) return null

  function clearAllFilters() {
    replaceSearchParams({
      ...Object.fromEntries(clearableKeys.map((key) => [key, undefined])),
      offset: 0,
    })
  }

  return (
    <Panel aria-label="Applied constraint filters" sx={{ p: 1.25 }}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ alignItems: { md: 'center' } }}>
        <Typography color="text.secondary" sx={{ fontWeight: 800, minWidth: 92, textTransform: 'uppercase' }} variant="caption">
          {filters.length} active
        </Typography>
        <Stack direction="row" sx={{ flex: 1, flexWrap: 'wrap', gap: 0.75, minWidth: 0 }}>
          {visibleFilters.map((filter) => (
            <Chip
              key={filter.key}
              label={`${filter.label}: ${readableValue(filter.value)}`}
              onDelete={() => replaceSearchParams({ [filter.key]: undefined, offset: 0 })}
              size="small"
              variant="outlined"
            />
          ))}
          {hiddenCount > 0 ? (
            <Typography color="text.secondary" sx={{ alignSelf: 'center' }} variant="caption">
              +{hiddenCount} more in advanced filters
            </Typography>
          ) : null}
        </Stack>
        <Button onClick={clearAllFilters} size="small" startIcon={<ClearAllIcon fontSize="small" />} variant="text">
          Clear filters
        </Button>
      </Stack>
    </Panel>
  )
}
