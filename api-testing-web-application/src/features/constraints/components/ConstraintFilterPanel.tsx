import FilterListIcon from '@mui/icons-material/FilterList'
import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined'
import SearchIcon from '@mui/icons-material/Search'
import { Button, Chip, InputAdornment, MenuItem, Stack, TextField, Tooltip, Typography } from '@mui/material'

import type {
  CombinationFacetsResponse,
  ConstraintFacetBucketResponse,
  ConstraintFacetsResponse,
  InvariantExplorerFacetsResponse,
} from '../../../shared/api/generated/model'
import { replaceSearchParams } from '../../../shared/lib/navigation'
import { DebouncedTextField } from '../../../shared/ui/DebouncedTextField'
import { Panel } from '../../../shared/ui/Panel'
import { TOUR_ANCHORS, tourAnchor } from '../../product-tour/tourAnchors'
import type { ConstraintTab, ConstraintsPageSearch } from '../ConstraintsPage'

type ConstraintFilterPanelProps = {
  combinationFacets?: CombinationFacetsResponse
  constraintFacets?: ConstraintFacetsResponse
  invariantFacets?: InvariantExplorerFacetsResponse
  onAdvancedOpen: () => void
  search: ConstraintsPageSearch
  tab: ConstraintTab
}

function booleanSelectValue(value: boolean | undefined) {
  if (value === undefined) return ''
  return value ? 'true' : 'false'
}

function booleanSearchValue(value: string) {
  return value === '' ? undefined : value
}

function selectOptions(buckets: ConstraintFacetBucketResponse[] | undefined, selected?: string) {
  const values = buckets?.map((bucket) => bucket.key) ?? []
  return selected && !values.includes(selected) ? [selected, ...values] : values
}

function FacetPreviewGroup({
  buckets,
  label,
  onSelect,
  selectedValue,
}: {
  buckets?: ConstraintFacetBucketResponse[]
  label: string
  onSelect: (value: string | undefined) => void
  selectedValue?: string
}) {
  const visibleBuckets = buckets?.slice(0, 2) ?? []
  if (visibleBuckets.length === 0) return null

  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
      <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
        {label}
      </Typography>
      {visibleBuckets.map((bucket) => {
        const selected = selectedValue === bucket.key
        return (
          <Chip
            color={selected ? 'primary' : 'default'}
            key={`${label}:${bucket.key}`}
            label={`${bucket.key} ${bucket.count}`}
            onClick={() => onSelect(selected ? undefined : bucket.key)}
            size="small"
            variant={selected ? 'filled' : 'outlined'}
          />
        )
      })}
    </Stack>
  )
}

export function ConstraintFilterPanel({
  combinationFacets,
  constraintFacets,
  invariantFacets,
  onAdvancedOpen,
  search,
  tab,
}: ConstraintFilterPanelProps) {
  const showCombinationFacets = tab === 'combination'
  const showConstraintFacets = tab === 'explorer'
  const showInvariantFacets = tab === 'invariants'
  const canUseExplorerFilters = tab === 'combination' || tab === 'explorer' || tab === 'invariants'

  return (
    <Panel
      actions={
        <Button onClick={onAdvancedOpen} size="small" startIcon={<FilterListIcon fontSize="small" />} variant="outlined">
          Advanced filters
        </Button>
      }
      subtitle="Use the top row for common triage. Keep deeper facets and grouping in the drawer."
      title="Find oracle signals"
      {...tourAnchor(TOUR_ANCHORS.constraintsFilters)}
    >
      <Stack spacing={1.5}>
        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1.25}>
          <DebouncedTextField
            fullWidth
            label="Search constraints"
            onDebouncedChange={(value) => replaceSearchParams({ offset: 0, q: value })}
            size="small"
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" />
                  </InputAdornment>
                ),
              },
            }}
            value={search.q ?? ''}
          />
          <DebouncedTextField
            label="Operation"
            onDebouncedChange={(value) => replaceSearchParams({ offset: 0, operationId: value })}
            size="small"
            sx={{ minWidth: { xs: '100%', lg: 240 } }}
            value={search.operationId ?? ''}
          />
          {tab === 'static' || tab === 'dynamic' ? (
            <DebouncedTextField
              label="Section"
              onDebouncedChange={(value) => replaceSearchParams({ offset: 0, section: value })}
              size="small"
              sx={{ minWidth: { xs: '100%', lg: 200 } }}
              value={search.section ?? ''}
            />
          ) : null}
        </Stack>

        {canUseExplorerFilters ? (
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25}>
            {tab === 'combination' ? (
              <TextField
                label="Status"
                onChange={(event) => replaceSearchParams({ offset: 0, status: event.target.value })}
                select
                size="small"
                sx={{ minWidth: 220 }}
                value={search.status ?? ''}
              >
                <MenuItem value="">Any status</MenuItem>
                {selectOptions(combinationFacets?.status, search.status).slice(0, 8).map((status) => (
                  <MenuItem key={status} value={status}>
                    {status}
                  </MenuItem>
                ))}
              </TextField>
            ) : tab === 'explorer' ? (
              <TextField
                label="Source"
                onChange={(event) => replaceSearchParams({ offset: 0, source: event.target.value })}
                select
                size="small"
                sx={{ minWidth: 180 }}
                value={search.source ?? ''}
              >
                <MenuItem value="">Any source</MenuItem>
                <MenuItem value="static">Static</MenuItem>
                <MenuItem value="dynamic">Dynamic</MenuItem>
                <MenuItem value="combined">Combined</MenuItem>
              </TextField>
            ) : (
              <TextField
                label="Readiness"
                onChange={(event) => replaceSearchParams({ offset: 0, oracleReadiness: event.target.value })}
                select
                size="small"
                sx={{ minWidth: 220 }}
                value={search.oracleReadiness ?? ''}
              >
                <MenuItem value="">Any readiness</MenuItem>
                {invariantFacets?.oracle_readiness.slice(0, 8).map((bucket) => (
                  <MenuItem key={bucket.key} value={bucket.key}>
                    {bucket.key}
                  </MenuItem>
                ))}
              </TextField>
            )}
            {tab === 'combination' ? (
              <TextField
                label="Resolved"
                onChange={(event) => replaceSearchParams({ offset: 0, resolved: booleanSearchValue(event.target.value) })}
                select
                size="small"
                sx={{ minWidth: 180 }}
                value={booleanSelectValue(search.resolved)}
              >
                <MenuItem value="">Any resolution</MenuItem>
                <MenuItem value="true">Resolved</MenuItem>
                <MenuItem value="false">Unresolved</MenuItem>
              </TextField>
            ) : (
              <DebouncedTextField
                label={tab === 'invariants' ? 'Raw invariant kind' : 'Constraint kind'}
                onDebouncedChange={(value) =>
                  replaceSearchParams(
                    tab === 'invariants'
                      ? { invariantKind: value, offset: 0 }
                      : { constraintKind: value, offset: 0 },
                  )
                }
                size="small"
                sx={{ minWidth: 220 }}
                value={tab === 'invariants' ? search.invariantKind ?? '' : search.constraintKind ?? ''}
              />
            )}
            <TextField
              label={tab === 'combination' ? 'Runtime evidence' : 'Assertion'}
              onChange={(event) =>
                replaceSearchParams(
                  tab === 'combination'
                    ? { hasRuntimeEvaluation: booleanSearchValue(event.target.value), offset: 0 }
                    : { assertionAvailable: booleanSearchValue(event.target.value), offset: 0 },
                )
              }
              select
              size="small"
              sx={{ minWidth: 180 }}
              value={tab === 'combination' ? booleanSelectValue(search.hasRuntimeEvaluation) : booleanSelectValue(search.assertionAvailable)}
            >
              <MenuItem value="">{tab === 'combination' ? 'Any evidence' : 'Any assertion'}</MenuItem>
              <MenuItem value="true">Available</MenuItem>
              <MenuItem value="false">Missing</MenuItem>
            </TextField>
          </Stack>
        ) : null}

        <Stack spacing={1}>
          <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
            <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
              Suggested facets
            </Typography>
            <Tooltip title="Source tells where a signal came from, Agreement shows static/dynamic alignment, and Assertion indicates executable oracle coverage. Use Advanced filters for the full facet list.">
              <HelpOutlineIcon color="action" fontSize="small" />
            </Tooltip>
          </Stack>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ flexWrap: 'wrap' }}>
            {showCombinationFacets ? (
              <>
                <FacetPreviewGroup
                  buckets={combinationFacets?.status}
                  label="Status"
                  onSelect={(value) => replaceSearchParams({ offset: 0, status: value })}
                  selectedValue={search.status}
                />
                <FacetPreviewGroup
                  buckets={combinationFacets?.relation}
                  label="Relation"
                  onSelect={(value) => replaceSearchParams({ offset: 0, relation: value })}
                  selectedValue={search.relation}
                />
                <FacetPreviewGroup
                  buckets={combinationFacets?.runtime_verdict}
                  label="Runtime verdict"
                  onSelect={(value) => replaceSearchParams({ offset: 0, runtimeVerdict: value })}
                  selectedValue={search.runtimeVerdict}
                />
              </>
            ) : null}
            {showConstraintFacets ? (
              <>
                <FacetPreviewGroup
                  buckets={constraintFacets?.source}
                  label="Source"
                  onSelect={(value) => replaceSearchParams({ offset: 0, source: value })}
                  selectedValue={search.source}
                />
                <FacetPreviewGroup
                  buckets={constraintFacets?.agreement_status}
                  label="Agreement"
                  onSelect={(value) => replaceSearchParams({ agreementStatus: value, offset: 0 })}
                  selectedValue={search.agreementStatus}
                />
              </>
            ) : null}
            {showInvariantFacets ? (
              <>
                <FacetPreviewGroup
                  buckets={invariantFacets?.oracle_readiness}
                  label="Readiness"
                  onSelect={(value) => replaceSearchParams({ offset: 0, oracleReadiness: value })}
                  selectedValue={search.oracleReadiness}
                />
                <FacetPreviewGroup
                  buckets={invariantFacets?.correlation_confidence}
                  label="Correlation"
                  onSelect={(value) => replaceSearchParams({ correlationConfidence: value, offset: 0 })}
                  selectedValue={search.correlationConfidence}
                />
              </>
            ) : null}
          </Stack>
        </Stack>
      </Stack>
    </Panel>
  )
}
