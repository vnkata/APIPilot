import FilterListIcon from '@mui/icons-material/FilterList'
import {
  Button,
  Chip,
  Drawer,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { useState } from 'react'

export type FacetBucket = {
  count: number
  key: string
}

export type FacetFilter = {
  buckets?: FacetBucket[]
  label: string
  onSelect: (value: string | undefined) => void
  selectedValue?: string
}

type FacetFilterBarProps = {
  filters: FacetFilter[]
  inlineCount?: number
}

function FacetGroup({ filter }: { filter: FacetFilter }) {
  const buckets = filter.buckets ?? []
  if (buckets.length === 0) return null

  return (
    <Stack spacing={0.75}>
      <Typography color="text.secondary" variant="caption">
        {filter.label}
      </Typography>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
        {buckets.slice(0, 8).map((bucket) => {
          const selected = filter.selectedValue === bucket.key
          return (
            <Chip
              color={selected ? 'primary' : 'default'}
              key={`${filter.label}:${bucket.key}`}
              label={`${bucket.key} (${bucket.count})`}
              onClick={() => filter.onSelect(selected ? undefined : bucket.key)}
              size="small"
              variant={selected ? 'filled' : 'outlined'}
            />
          )
        })}
      </Stack>
    </Stack>
  )
}

export function FacetFilterBar({ filters, inlineCount = 3 }: FacetFilterBarProps) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const theme = useTheme()
  const mobile = useMediaQuery(theme.breakpoints.down('md'))
  const primaryFilters = filters.slice(0, inlineCount)
  const secondaryFilters = filters.slice(inlineCount)

  return (
    <Stack spacing={1.5}>
      <Stack direction={{ xs: 'column', md: 'row' }} sx={{ flexWrap: 'wrap', gap: 1.5 }}>
        {primaryFilters.map((filter) => (
          <FacetGroup filter={filter} key={filter.label} />
        ))}
        {secondaryFilters.length > 0 ? (
          <Tooltip title="Show more filters">
            <Button
              onClick={() => setDrawerOpen(true)}
              size="small"
              startIcon={<FilterListIcon fontSize="small" />}
              variant="outlined"
            >
              More filters
            </Button>
          </Tooltip>
        ) : null}
      </Stack>
      <Drawer anchor={mobile ? 'bottom' : 'right'} onClose={() => setDrawerOpen(false)} open={drawerOpen}>
        <Stack spacing={2} sx={{ maxWidth: '100%', p: 2, width: mobile ? 'auto' : 360 }}>
          <Typography component="h2" variant="h3">
            More filters
          </Typography>
          {secondaryFilters.map((filter) => (
            <FacetGroup filter={filter} key={filter.label} />
          ))}
        </Stack>
      </Drawer>
    </Stack>
  )
}
