import CancelIcon from '@mui/icons-material/Cancel'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import VisibilityIcon from '@mui/icons-material/Visibility'
import {
  Alert,
  Button,
  Chip,
  MenuItem,
  Stack,
  TextField,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useQueryClient } from '@tanstack/react-query'
import { useMemo } from 'react'

import type { ExecutionResponse } from '../../shared/api/generated/model'
import { normalizeApiError } from '../../shared/api/errors'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { GuidanceCallout } from '../../shared/ui/Guidance'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { builderQueryKeys, useCancelExecution, useExecutions } from './api'
import {
  builderPath,
  encodePathPart,
  executionCanCancel,
  executionStatusColor,
} from './builderUtils'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'

export type ExecutionsPageSearch = {
  mode?: string
  status?: string
}

type ExecutionsPageProps = {
  search: ExecutionsPageSearch
}

export function ExecutionsPage({ search }: ExecutionsPageProps) {
  const queryClient = useQueryClient()
  const executionsQuery = useExecutions({
    query: {
      refetchInterval: (query) => {
        const executions = query.state.data?.executions ?? []
        return executions.some((execution) => executionCanCancel(execution)) ? 1_500 : false
      },
    },
  })
  const cancelExecution = useCancelExecution({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: builderQueryKeys.executions() })
      },
    },
  })
  const rows = (executionsQuery.data?.executions ?? []).filter((execution) => {
    if (search.status && execution.status !== search.status) return false
    if (search.mode && execution.mode !== search.mode) return false
    return true
  })
  const cancelError = cancelExecution.error ? normalizeApiError(cancelExecution.error) : undefined
  const activeCount = (executionsQuery.data?.executions ?? []).filter((execution) => executionCanCancel(execution)).length
  const columns = useMemo<GridColDef<ExecutionResponse>[]>(
    () => [
      { field: 'execution_id', flex: 1.2, headerName: 'Execution', minWidth: 220 },
      { field: 'mode', headerName: 'Mode', minWidth: 110 },
      {
        field: 'status',
        headerName: 'Status',
        minWidth: 140,
        renderCell: (params) => (
          <Chip
            color={executionStatusColor(params.row.status)}
            label={params.row.status}
            size="small"
            variant="outlined"
          />
        ),
      },
      { field: 'run_config_id', flex: 1, headerName: 'Config', minWidth: 180 },
      { field: 'created_at', headerName: 'Created', minWidth: 180 },
      {
        field: 'actions',
        headerName: 'Actions',
        minWidth: 360,
        sortable: false,
        renderCell: (params) => (
          <Stack direction="row" spacing={1}>
            <Button
              component="a"
              href={builderPath(`/executions/${encodePathPart(params.row.execution_id)}`)}
              size="small"
              startIcon={<VisibilityIcon />}
            >
              Open detail
            </Button>
            {params.row.run_name ? (
              <Button
                component="a"
                href={`/runs/${encodePathPart(params.row.run_name)}`}
                size="small"
                startIcon={<OpenInNewIcon />}
              >
                Open generated run
              </Button>
            ) : null}
            {executionCanCancel(params.row) ? (
              <Button
                color="warning"
                onClick={() => cancelExecution.mutate({ executionId: params.row.execution_id })}
                size="small"
                startIcon={<CancelIcon />}
              >
                Cancel
              </Button>
            ) : null}
          </Stack>
        ),
      },
    ],
    [cancelExecution],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Button component="a" href={builderPath('/run-configs/new')} variant="contained">
            New run config
          </Button>
        }
        eyebrow="Builder"
        subtitle={`${activeCount} active executions. Dry-run execution is deterministic; live execution remains guarded.`}
        title="Execution Center"
        {...tourAnchor(TOUR_ANCHORS.builderExecutionsHeader)}
      />
      <GuidanceCallout
        bullets={[
          'Queued, running, and cancel requested executions poll automatically.',
          'Completed executions may expose an Open generated run action.',
          'Cancel is available only while the backend reports an active status.',
        ]}
        title="Execution status guide"
      />
      <Stack direction="row" spacing={1} {...tourAnchor(TOUR_ANCHORS.builderExecutionsFilters)}>
        <TextField
          label="Status filter"
          onChange={(event) => replaceSearchParams({ status: event.target.value || undefined })}
          select
          size="small"
          value={search.status ?? ''}
        >
          <MenuItem value="">All statuses</MenuItem>
          <MenuItem value="queued">Queued</MenuItem>
          <MenuItem value="running">Running</MenuItem>
          <MenuItem value="cancel_requested">Cancel requested</MenuItem>
          <MenuItem value="completed">Completed</MenuItem>
          <MenuItem value="failed">Failed</MenuItem>
          <MenuItem value="cancelled">Cancelled</MenuItem>
        </TextField>
        <TextField
          label="Mode filter"
          onChange={(event) => replaceSearchParams({ mode: event.target.value || undefined })}
          select
          size="small"
          value={search.mode ?? ''}
        >
          <MenuItem value="">All modes</MenuItem>
          <MenuItem value="dry_run">Dry run</MenuItem>
          <MenuItem value="live">Live</MenuItem>
        </TextField>
      </Stack>
      {cancelError ? <Alert severity="error">{cancelError.message}</Alert> : null}
      <QueryState
        empty={rows.length === 0}
        emptyDescription="Create a run config and start a dry-run execution to populate the queue."
        emptyTitle="No executions"
        error={executionsQuery.error}
        isError={executionsQuery.isError}
        isLoading={executionsQuery.isLoading}
        onRetry={() => void executionsQuery.refetch()}
      >
        <ServerDataGridPanel
          ariaLabel="executions"
          columns={columns}
          getRowId={(row) => row.execution_id}
          paginationModel={{ page: 0, pageSize: 25 }}
          rowCount={rows.length}
          rows={rows}
          {...tourAnchor(TOUR_ANCHORS.builderExecutionsTable)}
        />
      </QueryState>
    </Stack>
  )
}
