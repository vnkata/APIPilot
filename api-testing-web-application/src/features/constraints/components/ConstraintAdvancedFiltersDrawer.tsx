import CloseIcon from '@mui/icons-material/Close'
import {
  Box,
  Button,
  Chip,
  Divider,
  Drawer,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'

import type {
  CombinationFacetsResponse,
  ConstraintFacetBucketResponse,
  ConstraintFacetsResponse,
  GroupCountResponse,
  InvariantExplorerFacetsResponse,
} from '../../../shared/api/generated/model'
import { replaceSearchParams } from '../../../shared/lib/navigation'
import { DebouncedTextField } from '../../../shared/ui/DebouncedTextField'
import type { ConstraintTab, ConstraintsPageSearch } from '../ConstraintsPage'
import type { MatrixBy } from '../constraintViewModels'

type ConstraintAdvancedFiltersDrawerProps = {
  activeGroups: GroupCountResponse[]
  combinationFacets?: CombinationFacetsResponse
  constraintFacets?: ConstraintFacetsResponse
  invariantFacets?: InvariantExplorerFacetsResponse
  onApplyGroupFilter: (key: string | null | undefined) => void
  onClose: () => void
  open: boolean
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

function selectedBoolean(value: boolean | undefined) {
  if (value === undefined) return undefined
  return String(value)
}

function FacetGroup({
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
  if (!buckets || buckets.length === 0) return null

  return (
    <Stack spacing={0.75}>
      <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
        {label}
      </Typography>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
        {buckets.map((bucket) => {
          const selected = selectedValue === bucket.key
          return (
            <Chip
              color={selected ? 'primary' : 'default'}
              key={`${label}:${bucket.key}`}
              label={`${bucket.key} (${bucket.count})`}
              onClick={() => onSelect(selected ? undefined : bucket.key)}
              size="small"
              variant={selected ? 'filled' : 'outlined'}
            />
          )
        })}
      </Stack>
    </Stack>
  )
}

export function ConstraintAdvancedFiltersDrawer({
  activeGroups,
  combinationFacets,
  constraintFacets,
  invariantFacets,
  onApplyGroupFilter,
  onClose,
  open,
  search,
  tab,
}: ConstraintAdvancedFiltersDrawerProps) {
  const theme = useTheme()
  const mobile = useMediaQuery(theme.breakpoints.down('md'))
  const isCombinationTab = tab === 'combination'
  const isInvariantTab = tab === 'invariants'
  const isLegacyTab = tab === 'static' || tab === 'dynamic'

  return (
    <Drawer anchor={mobile ? 'bottom' : 'right'} onClose={onClose} open={open}>
      <Box
        aria-label="Advanced constraint filters"
        role="dialog"
        sx={{
          maxHeight: mobile ? '88vh' : '100vh',
          maxWidth: '100%',
          overflow: 'auto',
          p: 2,
          width: mobile ? 'auto' : 420,
        }}
      >
        <Stack spacing={2}>
          <Stack direction="row" sx={{ alignItems: 'flex-start', gap: 1 }}>
            <Stack spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
              <Typography component="h2" variant="h3">
                Advanced filters
              </Typography>
              <Typography color="text.secondary" variant="body2">
                Use precise facets, grouping, and property filters without crowding the workbench.
              </Typography>
            </Stack>
            <Tooltip title="Close advanced filters">
              <IconButton aria-label="Close advanced filters" onClick={onClose} size="small">
                <CloseIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>

          <Divider />

          <Stack spacing={1.25}>
            <Typography component="h3" variant="h3">
              Query fields
            </Typography>
            <DebouncedTextField
              label="Section"
              onDebouncedChange={(value) => replaceSearchParams({ offset: 0, section: value })}
              size="small"
              value={search.section ?? ''}
            />
            <DebouncedTextField
              label="Property path"
              onDebouncedChange={(value) => replaceSearchParams({ offset: 0, propertyPath: value })}
              size="small"
              value={search.propertyPath ?? ''}
            />
            <DebouncedTextField
              label="Property prefix"
              onDebouncedChange={(value) => replaceSearchParams({ offset: 0, propertyPrefix: value })}
              size="small"
              value={search.propertyPrefix ?? ''}
            />
            {isCombinationTab ? (
              <>
                <DebouncedTextField
                  label="Status"
                  onDebouncedChange={(value) => replaceSearchParams({ offset: 0, status: value })}
                  size="small"
                  value={search.status ?? ''}
                />
                <DebouncedTextField
                  label="Verdict"
                  onDebouncedChange={(value) => replaceSearchParams({ offset: 0, verdict: value })}
                  size="small"
                  value={search.verdict ?? ''}
                />
              </>
            ) : !isInvariantTab ? (
              <>
                <DebouncedTextField
                  disabled={isLegacyTab}
                  label="Agreement"
                  onDebouncedChange={(value) => replaceSearchParams({ agreementStatus: value, offset: 0 })}
                  size="small"
                  value={search.agreementStatus ?? ''}
                />
                <DebouncedTextField
                  disabled={isLegacyTab}
                  label="Source type"
                  onDebouncedChange={(value) => replaceSearchParams({ offset: 0, sourceType: value })}
                  size="small"
                  value={search.sourceType ?? ''}
                />
              </>
            ) : (
              <>
                <DebouncedTextField
                  label="Oracle readiness"
                  onDebouncedChange={(value) => replaceSearchParams({ offset: 0, oracleReadiness: value })}
                  size="small"
                  value={search.oracleReadiness ?? ''}
                />
                <DebouncedTextField
                  label="Correlation"
                  onDebouncedChange={(value) => replaceSearchParams({ correlationConfidence: value, offset: 0 })}
                  size="small"
                  value={search.correlationConfidence ?? ''}
                />
                <DebouncedTextField
                  label="Raw invariant type"
                  onDebouncedChange={(value) => replaceSearchParams({ invariantType: value, offset: 0 })}
                  size="small"
                  value={search.invariantType ?? ''}
                />
              </>
            )}
            <TextField
              label={isCombinationTab ? 'Resolved' : 'Assertion'}
              onChange={(event) =>
                replaceSearchParams(
                  isCombinationTab
                    ? { offset: 0, resolved: booleanSearchValue(event.target.value) }
                    : { assertionAvailable: booleanSearchValue(event.target.value), offset: 0 },
                )
              }
              select
              size="small"
              value={isCombinationTab ? booleanSelectValue(search.resolved) : booleanSelectValue(search.assertionAvailable)}
            >
              <MenuItem value="">{isCombinationTab ? 'Any resolution' : 'Any assertion'}</MenuItem>
              <MenuItem value="true">{isCombinationTab ? 'Resolved' : 'Available'}</MenuItem>
              <MenuItem value="false">{isCombinationTab ? 'Unresolved' : 'Missing'}</MenuItem>
            </TextField>
            {isCombinationTab ? (
              <>
                <TextField
                  label="Counter-example"
                  onChange={(event) => replaceSearchParams({ hasCounterExample: booleanSearchValue(event.target.value), offset: 0 })}
                  select
                  size="small"
                  value={booleanSelectValue(search.hasCounterExample)}
                >
                  <MenuItem value="">Any counter-example</MenuItem>
                  <MenuItem value="true">Available</MenuItem>
                  <MenuItem value="false">Missing</MenuItem>
                </TextField>
                <TextField
                  label="Runtime evaluation"
                  onChange={(event) => replaceSearchParams({ hasRuntimeEvaluation: booleanSearchValue(event.target.value), offset: 0 })}
                  select
                  size="small"
                  value={booleanSelectValue(search.hasRuntimeEvaluation)}
                >
                  <MenuItem value="">Any runtime evaluation</MenuItem>
                  <MenuItem value="true">Available</MenuItem>
                  <MenuItem value="false">Missing</MenuItem>
                </TextField>
                <TextField
                  label="Validation cases"
                  onChange={(event) => replaceSearchParams({ hasValidationCases: booleanSearchValue(event.target.value), offset: 0 })}
                  select
                  size="small"
                  value={booleanSelectValue(search.hasValidationCases)}
                >
                  <MenuItem value="">Any validation cases</MenuItem>
                  <MenuItem value="true">Available</MenuItem>
                  <MenuItem value="false">Missing</MenuItem>
                </TextField>
              </>
            ) : null}
            <TextField
              label="Group by"
              onChange={(event) => replaceSearchParams({ groupBy: event.target.value, offset: 0 })}
              select
              size="small"
              value={search.groupBy ?? ''}
            >
              <MenuItem value="">No grouping</MenuItem>
              <MenuItem value="source">Source</MenuItem>
              <MenuItem value="operation_id">Operation</MenuItem>
              <MenuItem value="section">Section</MenuItem>
              <MenuItem value="constraint_kind">Constraint kind</MenuItem>
              <MenuItem value="source_type">Source type</MenuItem>
              <MenuItem value="agreement_status">Agreement</MenuItem>
              <MenuItem value="assertion_available">Assertion</MenuItem>
              <MenuItem value="status">Combination status</MenuItem>
              <MenuItem value="verdict">Verdict</MenuItem>
              <MenuItem value="resolved">Resolved</MenuItem>
              <MenuItem value="has_counter_example">Counter-example</MenuItem>
              <MenuItem value="has_runtime_evaluation">Runtime evaluation</MenuItem>
              <MenuItem value="has_validation_cases">Validation cases</MenuItem>
              <MenuItem value="invariant_kind">Raw invariant kind</MenuItem>
              <MenuItem value="invariant_type">Raw invariant type</MenuItem>
              <MenuItem value="oracle_readiness">Oracle readiness</MenuItem>
              <MenuItem value="correlation_confidence">Correlation</MenuItem>
            </TextField>
            <TextField
              label="Matrix by"
              onChange={(event) => replaceSearchParams({ matrixBy: event.target.value as MatrixBy })}
              select
              size="small"
              value={search.matrixBy ?? 'source'}
            >
              <MenuItem value="source">Source</MenuItem>
              <MenuItem value="kind">Kind</MenuItem>
              <MenuItem value="readiness">Readiness</MenuItem>
            </TextField>
          </Stack>

          <Divider />

          <Stack spacing={1.25}>
            <Typography component="h3" variant="h3">
              Facets
            </Typography>
            {isCombinationTab ? (
              <>
                <FacetGroup
                  buckets={combinationFacets?.status}
                  label="Status"
                  onSelect={(value) => replaceSearchParams({ offset: 0, status: value })}
                  selectedValue={search.status}
                />
                <FacetGroup
                  buckets={combinationFacets?.verdict}
                  label="Verdict"
                  onSelect={(value) => replaceSearchParams({ offset: 0, verdict: value })}
                  selectedValue={search.verdict}
                />
                <FacetGroup
                  buckets={combinationFacets?.resolved}
                  label="Resolved"
                  onSelect={(value) => replaceSearchParams({ offset: 0, resolved: value })}
                  selectedValue={selectedBoolean(search.resolved)}
                />
                <FacetGroup
                  buckets={combinationFacets?.has_counter_example}
                  label="Counter-example"
                  onSelect={(value) => replaceSearchParams({ hasCounterExample: value, offset: 0 })}
                  selectedValue={selectedBoolean(search.hasCounterExample)}
                />
                <FacetGroup
                  buckets={combinationFacets?.has_runtime_evaluation}
                  label="Runtime evaluation"
                  onSelect={(value) => replaceSearchParams({ hasRuntimeEvaluation: value, offset: 0 })}
                  selectedValue={selectedBoolean(search.hasRuntimeEvaluation)}
                />
                <FacetGroup
                  buckets={combinationFacets?.has_validation_cases}
                  label="Validation cases"
                  onSelect={(value) => replaceSearchParams({ hasValidationCases: value, offset: 0 })}
                  selectedValue={selectedBoolean(search.hasValidationCases)}
                />
              </>
            ) : isInvariantTab ? (
              <>
                <FacetGroup
                  buckets={invariantFacets?.oracle_readiness}
                  label="Oracle readiness"
                  onSelect={(value) => replaceSearchParams({ offset: 0, oracleReadiness: value })}
                  selectedValue={search.oracleReadiness}
                />
                <FacetGroup
                  buckets={invariantFacets?.correlation_confidence}
                  label="Correlation"
                  onSelect={(value) => replaceSearchParams({ correlationConfidence: value, offset: 0 })}
                  selectedValue={search.correlationConfidence}
                />
                <FacetGroup
                  buckets={invariantFacets?.invariant_kind}
                  label="Raw invariant kind"
                  onSelect={(value) => replaceSearchParams({ invariantKind: value, offset: 0 })}
                  selectedValue={search.invariantKind}
                />
                <FacetGroup
                  buckets={invariantFacets?.invariant_type}
                  label="Raw invariant type"
                  onSelect={(value) => replaceSearchParams({ invariantType: value, offset: 0 })}
                  selectedValue={search.invariantType}
                />
                <FacetGroup
                  buckets={invariantFacets?.assertion_available}
                  label="Assertion"
                  onSelect={(value) => replaceSearchParams({ assertionAvailable: value, offset: 0 })}
                  selectedValue={selectedBoolean(search.assertionAvailable)}
                />
              </>
            ) : (
              <>
                <FacetGroup
                  buckets={constraintFacets?.source}
                  label="Source"
                  onSelect={(value) => replaceSearchParams({ offset: 0, source: value })}
                  selectedValue={search.source}
                />
                <FacetGroup
                  buckets={constraintFacets?.agreement_status}
                  label="Agreement"
                  onSelect={(value) => replaceSearchParams({ agreementStatus: value, offset: 0 })}
                  selectedValue={search.agreementStatus}
                />
                <FacetGroup
                  buckets={constraintFacets?.constraint_kind}
                  label="Constraint kind"
                  onSelect={(value) => replaceSearchParams({ constraintKind: value, offset: 0 })}
                  selectedValue={search.constraintKind}
                />
                <FacetGroup
                  buckets={constraintFacets?.section}
                  label="Section"
                  onSelect={(value) => replaceSearchParams({ offset: 0, section: value })}
                  selectedValue={search.section}
                />
                <FacetGroup
                  buckets={constraintFacets?.source_type}
                  label="Source type"
                  onSelect={(value) => replaceSearchParams({ offset: 0, sourceType: value })}
                  selectedValue={search.sourceType}
                />
                <FacetGroup
                  buckets={constraintFacets?.assertion_available}
                  label="Assertion"
                  onSelect={(value) => replaceSearchParams({ assertionAvailable: value, offset: 0 })}
                  selectedValue={selectedBoolean(search.assertionAvailable)}
                />
              </>
            )}
          </Stack>

          {activeGroups.length > 0 ? (
            <>
              <Divider />
              <Stack spacing={1.25}>
                <Typography component="h3" variant="h3">
                  Current groups
                </Typography>
                <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                  {activeGroups.map((group) => (
                    <Chip
                      key={`${group.key ?? 'empty'}-${group.count}`}
                      label={`${group.key ?? 'empty'} (${group.count})`}
                      onClick={() => onApplyGroupFilter(group.key)}
                      size="small"
                      variant="outlined"
                    />
                  ))}
                </Stack>
              </Stack>
            </>
          ) : null}

          <Button onClick={onClose} variant="contained">
            Done
          </Button>
        </Stack>
      </Box>
    </Drawer>
  )
}
