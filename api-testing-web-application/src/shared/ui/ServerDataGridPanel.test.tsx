import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { GridColDef } from '@mui/x-data-grid'

import { renderWithProviders } from '../../test/renderWithProviders'
import { ServerDataGridPanel } from './ServerDataGridPanel'

type TestRow = {
  id: string
  name: string
  risk: string
}

const rows: TestRow[] = [
  { id: 'row-1', name: 'ListItems', risk: 'high' },
]

const columns: GridColDef<TestRow>[] = [
  { field: 'id', headerName: 'ID', width: 140 },
  { field: 'name', headerName: 'Name', width: 180 },
  { field: 'risk', headerName: 'Risk', width: 140 },
]

describe('ServerDataGridPanel', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('shows table power affordances and persists resettable column presets', async () => {
    const user = userEvent.setup()

    renderWithProviders(
      <ServerDataGridPanel
        ariaLabel="test table"
        columns={columns}
        copyCellOnDoubleClick
        getRowId={(row) => row.id}
        paginationModel={{ page: 0, pageSize: 25 }}
        rowCount={rows.length}
        rows={rows}
        tableLayout={{ page: 'workspace', runName: 'Run A', tableId: 'operations' }}
      />,
    )

    expect(screen.getByText(/table power/i)).toBeInTheDocument()
    expect(screen.getByText(/density:/i)).toBeInTheDocument()
    expect(screen.getByText(/double-click any cell/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^columns$/i }))
    await user.click(within(screen.getByRole('menu')).getByRole('checkbox', { name: /risk/i }))

    const rawValue = window.localStorage.getItem('apipilot.tablePowerPresets.v1') ?? ''
    expect(rawValue).toContain('operations')
    expect(rawValue).toContain('risk')

    await user.keyboard('{Escape}')
    await user.click(screen.getByRole('button', { name: /reset columns/i }))
    expect(window.localStorage.getItem('apipilot.tablePowerPresets.v1')).toContain('"columnVisibilityModel":{}')
  })
})
