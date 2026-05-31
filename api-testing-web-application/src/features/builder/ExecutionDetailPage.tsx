import CancelIcon from '@mui/icons-material/Cancel'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import {
  Alert,
  Button,
  Chip,
  Divider,
  Stack,
  Typography,
} from '@mui/material'
import { useQueryClient } from '@tanstack/react-query'

import { normalizeApiError } from '../../shared/api/errors'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import {
  builderQueryKeys,
  useCancelExecution,
  useExecution,
  useExecutionEvents,
} from './api'
import {
  encodePathPart,
  executionCanCancel,
  executionStatusColor,
  isActiveExecution,
  jsonPreview,
} from './builderUtils'

type ExecutionDetailPageProps = {
  executionId: string
}

export function ExecutionDetailPage({ executionId }: ExecutionDetailPageProps) {
  const queryClient = useQueryClient()
  const executionQuery = useExecution(executionId, {
    query: {
      refetchInterval: (query) => isActiveExecution(query.state.data?.status) ? 1_500 : false,
    },
  })
  const eventsQuery = useExecutionEvents(executionId, { after_sequence: 0 }, {
    query: {
      refetchInterval: () => isActiveExecution(executionQuery.data?.status) ? 1_500 : false,
    },
  })
  const cancelExecution = useCancelExecution({
    mutation: {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: builderQueryKeys.execution(executionId) })
        await queryClient.invalidateQueries({ queryKey: builderQueryKeys.executions() })
      },
    },
  })
  const execution = executionQuery.data
  const events = eventsQuery.data?.events ?? []
  const cancelError = cancelExecution.error ? normalizeApiError(cancelExecution.error) : undefined

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Stack direction="row" spacing={1}>
            {execution?.run_name ? (
              <Button
                component="a"
                href={`/runs/${encodePathPart(execution.run_name)}`}
                startIcon={<OpenInNewIcon />}
                variant="contained"
              >
                Open generated run
              </Button>
            ) : null}
            {executionCanCancel(execution) ? (
              <Button
                color="warning"
                onClick={() => cancelExecution.mutate({ executionId })}
                startIcon={<CancelIcon />}
                variant="outlined"
              >
                Cancel execution
              </Button>
            ) : null}
          </Stack>
        }
        eyebrow="Builder / Execution"
        subtitle={execution ? `${execution.mode} · ${execution.spec_id} · ${execution.run_config_id}` : executionId}
        title="Execution Detail"
      />
      {cancelError ? <Alert severity="error">{cancelError.message}</Alert> : null}
      <QueryState
        error={executionQuery.error ?? eventsQuery.error}
        isError={executionQuery.isError || eventsQuery.isError}
        isLoading={executionQuery.isLoading || eventsQuery.isLoading}
        onRetry={() => {
          void executionQuery.refetch()
          void eventsQuery.refetch()
        }}
      >
        {execution ? (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
              <Chip
                color={executionStatusColor(execution.status)}
                label={execution.status}
                variant="outlined"
              />
              <Typography color="text.secondary" variant="body2">
                Created {execution.created_at}
              </Typography>
              {execution.completed_at ? (
                <Typography color="text.secondary" variant="body2">
                  Completed {execution.completed_at}
                </Typography>
              ) : null}
            </Stack>
            <JsonBlock ariaLabel="execution summary" maxHeight={180} value={jsonPreview(execution.summary)} />
            <Stack aria-label="execution timeline" role="region" spacing={1}>
              <Typography component="h2" variant="h2">
                Event timeline
              </Typography>
              {events.map((event) => (
                <Stack
                  key={event.event_id}
                  spacing={1}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                    p: 1.5,
                  }}
                >
                  <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                    <Chip label={`#${event.sequence}`} size="small" />
                    <Typography sx={{ fontWeight: 700 }}>{event.message ?? event.event_type}</Typography>
                    {event.status ? <Chip label={event.status} size="small" variant="outlined" /> : null}
                  </Stack>
                  <Typography color="text.secondary" variant="caption">
                    {event.phase ?? 'execution'} · {event.created_at}
                  </Typography>
                  <Divider />
                  <JsonBlock ariaLabel={`${event.event_type} metadata`} maxHeight={180} value={jsonPreview(event.metadata)} />
                </Stack>
              ))}
            </Stack>
          </Stack>
        ) : null}
      </QueryState>
    </Stack>
  )
}
