import { Chip, Stack } from '@mui/material'

import { replaceSearchParams } from '../lib/navigation'

export type ActiveFilterChip = {
  key: string
  label: string
  value: string | number | boolean | undefined
}

type ActiveFilterChipsProps = {
  filters: ActiveFilterChip[]
}

export function ActiveFilterChips({ filters }: ActiveFilterChipsProps) {
  const activeFilters = filters.filter((filter) => filter.value !== undefined && filter.value !== '')

  if (activeFilters.length === 0) return null

  return (
    <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
      {activeFilters.map((filter) => (
        <Chip
          key={filter.key}
          label={`${filter.label}: ${String(filter.value)}`}
          onDelete={() => replaceSearchParams({ [filter.key]: undefined, offset: 0 })}
          size="small"
          variant="outlined"
        />
      ))}
    </Stack>
  )
}
