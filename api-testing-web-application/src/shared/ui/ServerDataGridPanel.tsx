import {
  Box,
  Button,
  Checkbox,
  Chip,
  FormControlLabel,
  Menu,
  Stack,
  Typography,
} from '@mui/material'
import {
  DataGrid,
  type DataGridProps,
  type GridColumnVisibilityModel,
  type GridValidRowModel,
} from '@mui/x-data-grid'
import { useState } from 'react'

import { useAppSelector } from '../../app/hooks'
import { selectWorkspacePreferences } from '../../features/workspace-preferences/workspacePreferencesSlice'
import {
  loadTableLayouts,
  loadTablePowerPresets,
  saveTableLayouts,
  saveTablePowerPresets,
  tableLayoutId,
  type WorkspacePageId,
  upsertTableLayout,
  upsertTablePowerPreset,
} from '../lib/workspaceStorage'

type ServerDataGridPanelProps<TRow extends GridValidRowModel> = Omit<
  DataGridProps<TRow>,
  | 'density'
  | 'disableRowSelectionOnClick'
  | 'paginationMode'
  | 'sortingMode'
> & {
  ariaLabel: string
  copyCellOnDoubleClick?: boolean
  tableLayout?: {
    page: WorkspacePageId
    runName: string
    tableId: string
  }
}

export function ServerDataGridPanel<TRow extends GridValidRowModel>({
  ariaLabel,
  columns,
  columnVisibilityModel: controlledColumnVisibilityModel,
  copyCellOnDoubleClick = false,
  onCellDoubleClick,
  onColumnVisibilityModelChange,
  sx,
  tableLayout,
  ...props
}: ServerDataGridPanelProps<TRow>) {
  const preferences = useAppSelector(selectWorkspacePreferences)
  const [columnMenuAnchor, setColumnMenuAnchor] = useState<HTMLElement | null>(null)
  const [storedColumnVisibilityModel, setStoredColumnVisibilityModel] = useState<GridColumnVisibilityModel>(() => {
    if (!tableLayout) return {}
    const id = tableLayoutId(tableLayout.runName, tableLayout.page, tableLayout.tableId)
    const tablePowerPreset = loadTablePowerPresets().find((layout) =>
      layout.runName === tableLayout.runName
      && layout.page === tableLayout.page
      && layout.tableId === tableLayout.tableId
      && layout.name === 'Default',
    )
    return tablePowerPreset?.columnVisibilityModel
      ?? loadTableLayouts().find((layout) => layout.id === id)?.columnVisibilityModel
      ?? {}
  })
  const columnVisibilityModel = controlledColumnVisibilityModel ?? storedColumnVisibilityModel

  function persistColumnVisibilityModel(nextModel: GridColumnVisibilityModel) {
    setStoredColumnVisibilityModel(nextModel)
    if (tableLayout) {
      saveTablePowerPresets(upsertTablePowerPreset(loadTablePowerPresets(), {
        columnVisibilityModel: nextModel,
        name: 'Default',
        page: tableLayout.page,
        runName: tableLayout.runName,
        tableId: tableLayout.tableId,
      }))
      saveTableLayouts(upsertTableLayout(loadTableLayouts(), {
        columnVisibilityModel: nextModel,
        page: tableLayout.page,
        runName: tableLayout.runName,
        tableId: tableLayout.tableId,
      }))
    }
  }

  const handleColumnVisibilityModelChange: NonNullable<DataGridProps<TRow>['onColumnVisibilityModelChange']> = (nextModel, details) => {
    persistColumnVisibilityModel(nextModel)
    onColumnVisibilityModelChange?.(nextModel, details)
  }

  const handleCellDoubleClick: NonNullable<DataGridProps<TRow>['onCellDoubleClick']> = (params, event, details) => {
    if (copyCellOnDoubleClick && params.value !== undefined && params.value !== null) {
      void navigator.clipboard?.writeText(String(params.value))
    }
    onCellDoubleClick?.(params, event, details)
  }

  return (
    <Box sx={{ minHeight: 360, minWidth: 0, width: '100%' }}>
      {tableLayout || copyCellOnDoubleClick ? (
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={1}
          sx={{ alignItems: { md: 'center' }, justifyContent: 'space-between', mb: 1 }}
        >
          <Stack direction="row" sx={{ alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Typography color="text.secondary" sx={{ fontWeight: 800, textTransform: 'uppercase' }} variant="caption">
              Table power
            </Typography>
            <Chip label={`Density: ${preferences.tableDensity}`} size="small" variant="outlined" />
            <Typography color="text.secondary" variant="caption">
              {copyCellOnDoubleClick ? 'Double-click any cell to copy its value.' : 'Customize visible columns.'}
            </Typography>
          </Stack>
          {tableLayout ? (
            <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
              <Button onClick={(event) => setColumnMenuAnchor(event.currentTarget)} size="small" variant="outlined">
                Columns
              </Button>
              <Button onClick={() => persistColumnVisibilityModel({})} size="small" variant="text">
                Reset columns
              </Button>
              <Menu anchorEl={columnMenuAnchor} onClose={() => setColumnMenuAnchor(null)} open={Boolean(columnMenuAnchor)}>
                <Stack spacing={0.5} sx={{ p: 1.5 }}>
                  {columns.map((column) => (
                    <FormControlLabel
                      key={column.field}
                      control={
                        <Checkbox
                          checked={columnVisibilityModel[column.field] !== false}
                          onChange={(event) => {
                            persistColumnVisibilityModel({
                              ...columnVisibilityModel,
                              [column.field]: event.target.checked,
                            })
                          }}
                          size="small"
                        />
                      }
                      label={column.headerName ?? column.field}
                    />
                  ))}
                </Stack>
              </Menu>
            </Stack>
          ) : null}
        </Stack>
      ) : null}
      <DataGrid
        aria-label={ariaLabel}
        columnVisibilityModel={columnVisibilityModel}
        columns={columns}
        density={preferences.tableDensity}
        disableRowSelectionOnClick
        onCellDoubleClick={handleCellDoubleClick}
        onColumnVisibilityModelChange={handleColumnVisibilityModelChange}
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
