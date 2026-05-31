import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import {
  Button,
  Chip,
  Stack,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'
import { useMemo } from 'react'

import type { SpecOperationResponse } from '../../shared/api/generated/model'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { HttpMethodBadge } from '../../shared/ui/SemanticBadges'
import { useSpec, useSpecOperations } from './api'
import { builderPath } from './builderUtils'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'

type SpecDetailPageProps = {
  specId: string
}

export function SpecDetailPage({ specId }: SpecDetailPageProps) {
  const specQuery = useSpec(specId)
  const operationsQuery = useSpecOperations(specId)
  const operations = operationsQuery.data?.operations ?? []
  const title = specQuery.data?.title ?? operationsQuery.data?.title ?? 'Spec detail'
  const columns = useMemo<GridColDef<SpecOperationResponse>[]>(
    () => [
      {
        field: 'display_operation_id',
        flex: 1,
        headerName: 'Operation',
        minWidth: 180,
        valueGetter: (_, row) => row.display_operation_id ?? row.operation_id,
      },
      {
        field: 'method',
        headerName: 'Method',
        minWidth: 110,
        renderCell: (params) => <HttpMethodBadge method={params.row.method} />,
      },
      { field: 'path', flex: 1, headerName: 'Path', minWidth: 180 },
      { field: 'summary', flex: 1, headerName: 'Summary', minWidth: 220 },
      {
        field: 'has_request_body',
        headerName: 'Body',
        minWidth: 110,
        renderCell: (params) => (
          <Chip label={params.row.has_request_body ? 'Body' : 'No body'} size="small" variant="outlined" />
        ),
      },
      {
        field: 'response_statuses',
        flex: 1,
        headerName: 'Responses',
        minWidth: 140,
        valueGetter: (_, row) => row.response_statuses.join(', '),
      },
    ],
    [],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Button
            component="a"
            href={`${builderPath('/run-configs/new')}?specId=${encodeURIComponent(specId)}`}
            startIcon={<PlayArrowIcon />}
            variant="contained"
          >
            Create run config
          </Button>
        }
        eyebrow="Builder / Spec"
        subtitle={`${specQuery.data?.filename ?? 'Uploaded spec'} · ${specQuery.data?.operation_count ?? operations.length} operations`}
        title={title}
        {...tourAnchor(TOUR_ANCHORS.builderSpecDetailHeader)}
      />
      <QueryState
        empty={operations.length === 0}
        emptyDescription="This spec did not expose operations in the backend preview."
        emptyTitle="No operations found"
        error={specQuery.error ?? operationsQuery.error}
        isError={specQuery.isError || operationsQuery.isError}
        isLoading={specQuery.isLoading || operationsQuery.isLoading}
        onRetry={() => {
          void specQuery.refetch()
          void operationsQuery.refetch()
        }}
      >
        <ServerDataGridPanel
          ariaLabel="spec operations"
          columns={columns}
          getRowId={(row) => row.operation_id}
          paginationModel={{ page: 0, pageSize: 25 }}
          rowCount={operations.length}
          rows={operations}
          {...tourAnchor(TOUR_ANCHORS.builderSpecOperations)}
        />
      </QueryState>
    </Stack>
  )
}
