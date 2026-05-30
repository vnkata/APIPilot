import { Chip, Divider, Stack, Typography } from '@mui/material'

import { useGetOperationApiV1RunsRunNameOperationGet } from '../api/generated/operations/operations'
import { encodeRoutePart } from '../lib/format'
import { replaceSearchParams } from '../lib/navigation'
import { AppLink } from './AppLink'
import { InvestigationDrawer } from './InvestigationDrawer'
import { JsonBlock } from './JsonBlock'
import { HttpMethodBadge, StatusCodeBadge } from './SemanticBadges'

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
    <InvestigationDrawer
      ariaLabel="Operation detail"
      error={operationQuery.error}
      isError={operationQuery.isError}
      isLoading={operationQuery.isLoading}
      onClose={handleClose}
      onRetry={() => void operationQuery.refetch()}
      open={open}
      subtitle={operationId}
      title="Operation detail"
    >
      {operationQuery.data ? (
        <Stack spacing={2}>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <HttpMethodBadge method={operationQuery.data.http_method} />
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
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            {Object.keys(operationQuery.data.responses ?? {}).length > 0 ? (
              Object.keys(operationQuery.data.responses ?? {}).map((status) => (
                <StatusCodeBadge key={status} statusCode={status} />
              ))
            ) : (
              <StatusCodeBadge statusCode={undefined} />
            )}
          </Stack>
          <JsonBlock maxHeight={220} value={operationQuery.data.responses} />
        </Stack>
      ) : null}
    </InvestigationDrawer>
  )
}
