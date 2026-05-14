import { Box } from '@mui/material'
import { DataGrid, type DataGridProps, type GridValidRowModel } from '@mui/x-data-grid'

type DataGridPanelProps<TRow extends GridValidRowModel> = Omit<
  DataGridProps<TRow>,
  'disableRowSelectionOnClick'
> & {
  ariaLabel: string
}

export function DataGridPanel<TRow extends GridValidRowModel>({
  ariaLabel,
  sx,
  ...props
}: DataGridPanelProps<TRow>) {
  return (
    <Box sx={{ minHeight: 280, width: '100%' }}>
      <DataGrid
        aria-label={ariaLabel}
        density="compact"
        disableRowSelectionOnClick
        pageSizeOptions={[10, 25, 50, 100, 200]}
        sx={{
          bgcolor: 'background.paper',
          borderColor: 'divider',
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
