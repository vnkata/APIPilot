import CloseIcon from '@mui/icons-material/Close'
import { useMemo, useState } from 'react'
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Drawer,
  IconButton,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'

import type {
  ConstraintEntryDetailResponse,
  InvariantDetailResponse,
  SortOrder,
} from '../../shared/api/generated/model'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { replaceSearchParams } from '../../shared/lib/navigation'
import {
  useDynamicConstraintEntries,
  useDynamicConstraintsSummary,
  useDynamicInvariants,
  useStaticConstraintEntries,
  useStaticConstraintsSummary,
} from './api'

export type ConstraintTab = 'dynamic' | 'invariants' | 'static'

export type ConstraintsPageSearch = {
  constraintTab: ConstraintTab
  groupBy?: string
  invariantType?: string
  limit: number
  offset: number
  operationId?: string
  q?: string
  section?: string
  sortBy?: string
  sortOrder?: SortOrder
}

type ConstraintsPageProps = {
  runName: string
  search: ConstraintsPageSearch
}

type ConstraintRow = ConstraintEntryDetailResponse & {
  id: string
}

type InvariantRow = InvariantDetailResponse & {
  id: string
}

function constraintRows(items: ConstraintEntryDetailResponse[]) {
  return items.map((item, index) => ({
    ...item,
    id: `${item.operation_id}:${item.section ?? 'dynamic'}:${item.property_path}:${index}`,
  }))
}

function invariantRows(items: InvariantDetailResponse[]) {
  return items.map((item, index) => ({
    ...item,
    id: `${item.operation_id ?? 'unknown'}:${item.pptname ?? 'ppt'}:${index}`,
  }))
}

export function ConstraintsPage({ runName, search }: ConstraintsPageProps) {
  const [selectedDetail, setSelectedDetail] = useState<ConstraintRow | InvariantRow | null>(null)
  const gridState = useUrlBackedGridState(search)
  const tab = search.constraintTab
  const staticSummaryQuery = useStaticConstraintsSummary(runName)
  const dynamicSummaryQuery = useDynamicConstraintsSummary(runName)
  const staticEntriesQuery = useStaticConstraintEntries(runName, {
    group_by: search.groupBy,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    q: search.q,
    section: search.section,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
  })
  const dynamicEntriesQuery = useDynamicConstraintEntries(runName, {
    group_by: search.groupBy,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    q: search.q,
    section: search.section,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
  })
  const invariantsQuery = useDynamicInvariants(runName, {
    group_by: search.groupBy,
    invariant_type: search.invariantType,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    q: search.q,
    sort_by: search.sortBy,
    sort_order: search.sortOrder,
  })

  const activeConstraintQuery = tab === 'dynamic' ? dynamicEntriesQuery : staticEntriesQuery
  const activeRows = useMemo(
    () => constraintRows(activeConstraintQuery.data?.items ?? []),
    [activeConstraintQuery.data?.items],
  )
  const activeInvariantRows = useMemo(
    () => invariantRows(invariantsQuery.data?.items ?? []),
    [invariantsQuery.data?.items],
  )
  const activeGroups =
    tab === 'invariants' ? invariantsQuery.data?.groups ?? [] : activeConstraintQuery.data?.groups ?? []
  const activePagination =
    tab === 'invariants' ? invariantsQuery.data?.pagination : activeConstraintQuery.data?.pagination
  const constraintColumns = useMemo<GridColDef<ConstraintRow>[]>(
    () => [
      {
        field: 'operation_id',
        flex: 1,
        headerName: 'Operation',
        minWidth: 160,
        renderCell: (params) => (
          <Button
            onClick={() => replaceSearchParams({ operationId: params.row.operation_id })}
            size="small"
          >
            {params.row.operation_id}
          </Button>
        ),
      },
      { field: 'section', flex: 0.8, headerName: 'Section', minWidth: 160 },
      { field: 'property_path', flex: 1.1, headerName: 'Property path', minWidth: 200 },
      {
        field: 'expression',
        flex: 1.8,
        headerName: 'Expression',
        minWidth: 280,
        renderCell: (params) => (
          <Button color="inherit" onClick={() => setSelectedDetail(params.row)} size="small">
            {params.row.expression}
          </Button>
        ),
      },
    ],
    [],
  )
  const invariantColumns = useMemo<GridColDef<InvariantRow>[]>(
    () => [
      {
        field: 'operation_id',
        flex: 1,
        headerName: 'Operation',
        minWidth: 160,
        renderCell: (params) =>
          params.row.operation_id ? (
            <Button
              onClick={() => replaceSearchParams({ operationId: params.row.operation_id })}
              size="small"
            >
              {params.row.operation_id}
            </Button>
          ) : null,
      },
      { field: 'invariant_type', flex: 1, headerName: 'Type', minWidth: 220 },
      { field: 'pptname', flex: 1, headerName: 'Ppt name', minWidth: 220 },
      {
        field: 'invariant',
        flex: 1.6,
        headerName: 'Invariant',
        minWidth: 280,
        renderCell: (params) => (
          <Button color="inherit" onClick={() => setSelectedDetail(params.row)} size="small">
            {params.row.invariant}
          </Button>
        ),
      },
      { field: 'postman_assertion', flex: 1.6, headerName: 'Assertion', minWidth: 280 },
    ],
    [],
  )

  function applyGroupFilter(key: string | null | undefined) {
    if (!key) return
    if (search.groupBy === 'operation_id') replaceSearchParams({ offset: 0, operationId: key })
    if (search.groupBy === 'section') replaceSearchParams({ offset: 0, section: key })
    if (search.groupBy === 'invariant_type') replaceSearchParams({ invariantType: key, offset: 0 })
  }

  return (
    <Stack spacing={2}>
      <PageHeader
        eyebrow="Constraint oracle workspace"
        title="Constraints and invariants"
        subtitle="Filter static constraints, dynamic constraints, and Daikon-derived invariants without copying server cache into Redux."
      />

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
              <TextField
                fullWidth
                label="Search constraints"
                onChange={(event) => {
                  replaceSearchParams({ offset: 0, q: event.target.value })
                }}
                size="small"
                value={search.q ?? ''}
              />
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Chip
                  label={`Static ${staticSummaryQuery.data?.constraint_count ?? 0}`}
                  size="small"
                />
                <Chip
                  label={`Dynamic ${dynamicSummaryQuery.data?.constraint_count ?? 0}`}
                  size="small"
                />
                <Chip
                  label={`Invariants ${dynamicSummaryQuery.data?.invariant_count ?? 0}`}
                  size="small"
                />
              </Stack>
            </Stack>

            <Tabs
              onChange={(_, value: ConstraintTab) => {
                replaceSearchParams({ constraintTab: value, offset: 0 })
              }}
              value={tab}
            >
              <Tab label="Static" value="static" />
              <Tab label="Dynamic" value="dynamic" />
              <Tab label="Invariants" value="invariants" />
            </Tabs>

            <FilterToolbar>
              <TextField
                label="Operation"
                onChange={(event) => replaceSearchParams({ offset: 0, operationId: event.target.value })}
                size="small"
                sx={{ minWidth: 220 }}
                value={search.operationId ?? ''}
              />
              <TextField
                label="Section"
                onChange={(event) => replaceSearchParams({ offset: 0, section: event.target.value })}
                size="small"
                sx={{ minWidth: 200 }}
                value={search.section ?? ''}
              />
              <TextField
                disabled={tab !== 'invariants'}
                label="Invariant type"
                onChange={(event) => replaceSearchParams({ invariantType: event.target.value, offset: 0 })}
                size="small"
                sx={{ minWidth: 220 }}
                value={search.invariantType ?? ''}
              />
              <TextField
                label="Group"
                onChange={(event) => replaceSearchParams({ groupBy: event.target.value, offset: 0 })}
                select
                size="small"
                sx={{ minWidth: 180 }}
                value={search.groupBy ?? ''}
              >
                <MenuItem value="">No grouping</MenuItem>
                <MenuItem value="operation_id">Operation</MenuItem>
                <MenuItem value="section">Section</MenuItem>
                <MenuItem value="invariant_type">Invariant type</MenuItem>
              </TextField>
            </FilterToolbar>

            <ActiveFilterChips
              filters={[
                { key: 'q', label: 'Search', value: search.q },
                { key: 'operationId', label: 'Operation', value: search.operationId },
                { key: 'section', label: 'Section', value: search.section },
                { key: 'invariantType', label: 'Invariant type', value: search.invariantType },
                { key: 'groupBy', label: 'Group', value: search.groupBy },
              ]}
            />

            {activeGroups.length > 0 ? (
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                {activeGroups.map((group) => (
                  <Chip
                    key={`${group.key ?? 'empty'}-${group.count}`}
                    label={`${group.key ?? 'empty'} (${group.count})`}
                    onClick={() => applyGroupFilter(group.key)}
                    size="small"
                  />
                ))}
              </Stack>
            ) : null}

            {tab === 'invariants' ? (
              <QueryState
                empty={activeInvariantRows.length === 0}
                error={invariantsQuery.error}
                isError={invariantsQuery.isError}
                isLoading={invariantsQuery.isLoading}
                onRetry={() => void invariantsQuery.refetch()}
              >
                <ServerDataGridPanel
                  ariaLabel="dynamic invariants"
                  columns={invariantColumns}
                  getRowId={(row) => row.id}
                  loading={invariantsQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={activePagination?.total ?? 0}
                  rows={activeInvariantRows}
                  sortModel={gridState.sortModel}
                />
              </QueryState>
            ) : (
              <QueryState
                empty={activeRows.length === 0}
                error={activeConstraintQuery.error}
                isError={activeConstraintQuery.isError}
                isLoading={activeConstraintQuery.isLoading}
                onRetry={() => void activeConstraintQuery.refetch()}
              >
                <ServerDataGridPanel
                  ariaLabel={`${tab} constraint entries`}
                  columns={constraintColumns}
                  getRowId={(row) => row.id}
                  loading={activeConstraintQuery.isFetching}
                  onPaginationModelChange={gridState.handlePaginationModelChange}
                  onSortModelChange={gridState.handleSortModelChange}
                  paginationModel={gridState.paginationModel}
                  rowCount={activePagination?.total ?? 0}
                  rows={activeRows}
                  sortModel={gridState.sortModel}
                />
              </QueryState>
            )}

            <Typography color="text.secondary" variant="body2">
              Query params: limit {search.limit}, offset {search.offset}, sort {search.sortBy ?? 'default'}.
            </Typography>
            <JsonBlock
              ariaLabel="constraint query metadata"
              maxHeight={180}
              value={{
                dynamicSummary: dynamicSummaryQuery.data,
                staticSummary: staticSummaryQuery.data,
              }}
            />
          </Stack>
        </CardContent>
      </Card>
      <Drawer
        anchor="right"
        onClose={() => setSelectedDetail(null)}
        open={Boolean(selectedDetail)}
        slotProps={{ paper: { sx: { maxWidth: '100%', width: { xs: '100%', sm: 520 } } } }}
      >
        <Box aria-label="Constraint detail" role="dialog" sx={{ p: 2 }}>
          <Stack spacing={2}>
            <Stack direction="row" sx={{ alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography component="h2" variant="h3">
                Constraint detail
              </Typography>
              <IconButton aria-label="Close constraint detail" onClick={() => setSelectedDetail(null)}>
                <CloseIcon />
              </IconButton>
            </Stack>
            <JsonBlock value={selectedDetail} />
          </Stack>
        </Box>
      </Drawer>
      <OperationDetailDrawer operationId={search.operationId} runName={runName} />
    </Stack>
  )
}
