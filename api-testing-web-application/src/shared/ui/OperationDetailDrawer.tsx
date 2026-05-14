import CloseIcon from '@mui/icons-material/Close'
import {
  Box,
  Chip,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'

import { useGetOperationApiV1RunsRunNameOperationGet } from '../api/generated/operations/operations'
import { encodeRoutePart } from '../lib/format'
import { replaceSearchParams } from '../lib/navigation'
import { AppLink } from './AppLink'
import { ApiErrorAlert } from './ApiErrorAlert'
import { JsonBlock } from './JsonBlock'
import { PageSkeleton } from './PageSkeleton'

type OperationDetailDrawerProps = {
  operationId?: string
  runName: string
}

export function OperationDetailDrawer({ operationId, runName }: OperationDetailDrawerProps) {
  const open = Boolean(operationId)
  const encodedRunName = encodeRoutePart(runName)
  const encodedOperationId = encodeURIComponent(operationId ?? '')
  const operationQuery = useGetOperationApiV1RunsRunNameOperationGet(
    runName,
    { operation_id: operationId ?? '' },
    { query: { enabled: open } },
  )

  function handleClose() {
    replaceSearchParams({ operationId: undefined })
  }

  return (
    <Drawer
      anchor="right"
      onClose={handleClose}
      open={open}
      slotProps={{
        paper: {
          sx: { maxWidth: '100%', width: { xs: '100%', sm: 520 } },
        },
      }}
      variant="persistent"
    >
      <Box
        aria-label="Operation detail"
        role="dialog"
        sx={{ height: '100%', overflow: 'auto', p: 2 }}
      >
        <Stack spacing={2}>
          <Stack direction="row" sx={{ alignItems: 'flex-start', gap: 1 }}>
            <Stack spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
              <Typography component="h2" variant="h3">
                Operation detail
              </Typography>
              <Typography color="text.secondary" noWrap variant="body2">
                {operationId}
              </Typography>
            </Stack>
            <Tooltip title="Close operation detail">
              <IconButton aria-label="Close operation detail" onClick={handleClose} size="small">
                <CloseIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Stack>

          {operationQuery.isLoading ? <PageSkeleton /> : null}
          {operationQuery.isError ? (
            <ApiErrorAlert error={operationQuery.error} onRetry={() => void operationQuery.refetch()} />
          ) : null}
          {operationQuery.data ? (
            <Stack spacing={2}>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Chip label={operationQuery.data.http_method?.toUpperCase() ?? 'UNKNOWN'} size="small" />
                <Chip label={operationQuery.data.path_template} size="small" variant="outlined" />
                <Chip
                  label={`${operationQuery.data.parameter_count} parameters`}
                  size="small"
                  variant="outlined"
                />
              </Stack>
              <Typography component="h3" variant="h3">
                {operationQuery.data.display_operation_id ?? operationQuery.data.operation_id}
              </Typography>
              <Divider />
              <Typography component="h4" variant="subtitle2">
                Related evidence
              </Typography>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <AppLink href={`/runs/${encodedRunName}/graph?operationId=${encodedOperationId}`}>
                  Graph
                </AppLink>
                <AppLink href={`/runs/${encodedRunName}/reports?operationId=${encodedOperationId}`}>
                  Reports
                </AppLink>
                <AppLink href={`/runs/${encodedRunName}/constraints?operationId=${encodedOperationId}`}>
                  Constraints
                </AppLink>
                <AppLink href={`/runs/${encodedRunName}/test-cases?operationId=${encodedOperationId}`}>
                  Test cases
                </AppLink>
              </Stack>
              <Divider />
              <Typography component="h4" variant="subtitle2">
                Parameters
              </Typography>
              <JsonBlock maxHeight={180} value={operationQuery.data.parameters} />
              <Typography component="h4" variant="subtitle2">
                Request body
              </Typography>
              <JsonBlock maxHeight={180} value={operationQuery.data.request_body} />
              <Typography component="h4" variant="subtitle2">
                Responses
              </Typography>
              <JsonBlock maxHeight={220} value={operationQuery.data.responses} />
            </Stack>
          ) : null}
        </Stack>
      </Box>
    </Drawer>
  )
}
