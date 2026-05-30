import type {
  GridPaginationModel,
  GridSortModel,
} from '@mui/x-data-grid'

import type {
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
} from '../../../shared/api/generated/model'
import { QueryState } from '../../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../../shared/ui/ServerDataGridPanel'
import type { ConstraintTab } from '../ConstraintsPage'
import type { MatrixBy } from '../constraintViewModels'
import type {
  ConstraintGridColumns,
  ConstraintQueryState,
  LegacyConstraintRow,
} from '../types'
import { ConstraintWorkbench } from './ConstraintWorkbench'
import { CurrentPageConstraintMatrix } from './CurrentPageConstraintMatrix'

type GridState = {
  handlePaginationModelChange: (model: GridPaginationModel) => void
  handleSortModelChange: (model: GridSortModel) => void
  paginationModel: GridPaginationModel
  sortModel: GridSortModel
}

type ConstraintResultsRegionProps = {
  columns: ConstraintGridColumns
  constraintsView: 'matrix' | 'table' | 'workbench'
  explorerQuery: ConstraintQueryState
  explorerRowCount: number
  explorerRows: ConstraintExplorerEntryResponse[]
  gridState: GridState
  invariantQuery: ConstraintQueryState
  invariantRowCount: number
  invariantRows: InvariantExplorerEntryResponse[]
  legacyQuery: ConstraintQueryState
  legacyRowCount: number
  legacyRows: LegacyConstraintRow[]
  matrixBy: MatrixBy
  onApplyMatrixFilter: (filter: Record<string, string | undefined>) => void
  onMatrixByChange: (value: MatrixBy) => void
  onSelectConstraint: (constraintId: string) => void
  onSelectInvariant: (invariantId: string) => void
  tab: ConstraintTab
}

export function ConstraintResultsRegion({
  columns,
  constraintsView,
  explorerQuery,
  explorerRowCount,
  explorerRows,
  gridState,
  invariantQuery,
  invariantRowCount,
  invariantRows,
  legacyQuery,
  legacyRowCount,
  legacyRows,
  matrixBy,
  onApplyMatrixFilter,
  onMatrixByChange,
  onSelectConstraint,
  onSelectInvariant,
  tab,
}: ConstraintResultsRegionProps) {
  if (constraintsView === 'workbench') {
    return (
      <QueryState
        empty={explorerRows.length === 0 && invariantRows.length === 0}
        error={explorerQuery.error ?? invariantQuery.error}
        isError={explorerQuery.isError || invariantQuery.isError}
        isLoading={explorerQuery.isLoading || invariantQuery.isLoading}
        onRetry={() => {
          void explorerQuery.refetch()
          void invariantQuery.refetch()
        }}
      >
        <ConstraintWorkbench
          constraints={explorerRows}
          invariants={invariantRows}
          matrixBy={matrixBy}
          onApplyFilter={onApplyMatrixFilter}
          onMatrixByChange={onMatrixByChange}
          onSelectConstraint={onSelectConstraint}
          onSelectInvariant={onSelectInvariant}
        />
      </QueryState>
    )
  }

  if (constraintsView === 'matrix') {
    return (
      <QueryState
        empty={explorerRows.length === 0 && invariantRows.length === 0}
        error={explorerQuery.error ?? invariantQuery.error}
        isError={explorerQuery.isError || invariantQuery.isError}
        isLoading={explorerQuery.isLoading || invariantQuery.isLoading}
        onRetry={() => {
          void explorerQuery.refetch()
          void invariantQuery.refetch()
        }}
      >
        <CurrentPageConstraintMatrix
          constraints={explorerRows}
          invariants={invariantRows}
          matrixBy={matrixBy}
          onApplyFilter={onApplyMatrixFilter}
        />
      </QueryState>
    )
  }

  if (tab === 'explorer') {
    return (
      <QueryState
        empty={explorerRows.length === 0}
        error={explorerQuery.error}
        isError={explorerQuery.isError}
        isLoading={explorerQuery.isLoading}
        onRetry={() => void explorerQuery.refetch()}
      >
        <ServerDataGridPanel
          ariaLabel="constraint explorer entries"
          columns={columns.explorer}
          getRowId={(row) => row.constraint_id}
          loading={explorerQuery.isFetching}
          onPaginationModelChange={gridState.handlePaginationModelChange}
          onRowClick={(params) => onSelectConstraint(params.row.constraint_id)}
          onSortModelChange={gridState.handleSortModelChange}
          paginationModel={gridState.paginationModel}
          rowCount={explorerRowCount}
          rows={explorerRows}
          sortModel={gridState.sortModel}
        />
      </QueryState>
    )
  }

  if (tab === 'invariants') {
    return (
      <QueryState
        empty={invariantRows.length === 0}
        error={invariantQuery.error}
        isError={invariantQuery.isError}
        isLoading={invariantQuery.isLoading}
        onRetry={() => void invariantQuery.refetch()}
      >
        <ServerDataGridPanel
          ariaLabel="invariant explorer entries"
          columns={columns.invariants}
          getRowId={(row) => row.invariant_id}
          loading={invariantQuery.isFetching}
          onPaginationModelChange={gridState.handlePaginationModelChange}
          onRowClick={(params) => onSelectInvariant(params.row.invariant_id)}
          onSortModelChange={gridState.handleSortModelChange}
          paginationModel={gridState.paginationModel}
          rowCount={invariantRowCount}
          rows={invariantRows}
          sortModel={gridState.sortModel}
        />
      </QueryState>
    )
  }

  return (
    <QueryState
      empty={legacyRows.length === 0}
      error={legacyQuery.error}
      isError={legacyQuery.isError}
      isLoading={legacyQuery.isLoading}
      onRetry={() => void legacyQuery.refetch()}
    >
      <ServerDataGridPanel
        ariaLabel={`${tab} constraint entries`}
        columns={columns.legacy}
        getRowId={(row) => row.id}
        loading={legacyQuery.isFetching}
        onPaginationModelChange={gridState.handlePaginationModelChange}
        onSortModelChange={gridState.handleSortModelChange}
        paginationModel={gridState.paginationModel}
        rowCount={legacyRowCount}
        rows={legacyRows}
        sortModel={gridState.sortModel}
      />
    </QueryState>
  )
}
