import type { GridColDef } from '@mui/x-data-grid'

import type {
  CombinationEntryResponse,
  ConstraintEntryDetailResponse,
  ConstraintExplorerEntryResponse,
  InvariantExplorerEntryResponse,
} from '../../shared/api/generated/model'

export type LegacyConstraintRow = ConstraintEntryDetailResponse & { id: string }

export type ConstraintGridColumns = {
  combination: GridColDef<CombinationEntryResponse>[]
  explorer: GridColDef<ConstraintExplorerEntryResponse>[]
  invariants: GridColDef<InvariantExplorerEntryResponse>[]
  legacy: GridColDef<LegacyConstraintRow>[]
}

export type ConstraintQueryState = {
  error: unknown
  isError: boolean
  isFetching: boolean
  isLoading: boolean
  refetch: () => unknown
}
