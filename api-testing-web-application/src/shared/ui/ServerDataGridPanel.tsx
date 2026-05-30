import { Box } from '@mui/material'
import {
  DataGrid,
  type DataGridProps,
  type GridValidRowModel,
} from '@mui/x-data-grid'

import { useAppSelector } from '../../app/hooks'
import { selectWorkspacePreferences } from '../../features/workspace-preferences/workspacePreferencesSlice'

type ServerDataGridPanelProps<TRow extends GridValidRowModel> = Omit<
  DataGridProps<TRow>,
  | 'density'
  | 'disableRowSelectionOnClick'
  | 'paginationMode'
  | 'sortingMode'
> & {
  ariaLabel: string
}

export function ServerDataGridPanel<TRow extends GridValidRowModel>({
  ariaLabel,
  sx,
  ...props
}: ServerDataGridPanelProps<TRow>) {
  const preferences = useAppSelector(selectWorkspacePreferences)

  return (
    <Box sx={{ minHeight: 360, minWidth: 0, width: '100%' }}>
      <DataGrid
        aria-label={ariaLabel}
        density={preferences.tableDensity}
        disableRowSelectionOnClick
        pageSizeOptions={[10, 25, 50, 100, 200]}
        paginationMode="server"
        sortingMode="server"
        sx={{
          bgcolor: (theme) => theme.apiTesting.surface.default,
          borderColor: (theme) => theme.apiTesting.border.default,
          '& .MuiDataGrid-cell': {
            alignItems: 'center',
            display: 'flex',
          },
          ...sx,
        }}
        {...props}
      />
    </Box>
  )
}
