import type { GridPaginationModel, GridSortModel } from '@mui/x-data-grid'

import { replaceSearchParams } from '../lib/navigation'

type UrlBackedGridSearch = {
  limit: number
  offset: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export function useUrlBackedGridState(search: UrlBackedGridSearch) {
  const page = Math.floor(search.offset / search.limit)
  const paginationModel: GridPaginationModel = { page, pageSize: search.limit }
  const sortModel: GridSortModel = search.sortBy
    ? [{ field: search.sortBy, sort: search.sortOrder ?? 'asc' }]
    : []

  function handlePaginationModelChange(model: GridPaginationModel) {
    replaceSearchParams({
      limit: model.pageSize,
      offset: model.page * model.pageSize,
    })
  }

  function handleSortModelChange(model: GridSortModel) {
    const [firstSort] = model
    replaceSearchParams({
      offset: 0,
      sortBy: firstSort?.field,
      sortOrder: firstSort?.sort,
    })
  }

  return {
    handlePaginationModelChange,
    handleSortModelChange,
    paginationModel,
    sortModel,
  }
}
