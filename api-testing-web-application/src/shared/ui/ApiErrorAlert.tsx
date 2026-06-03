import { Alert, AlertTitle, Button, Stack, Typography } from '@mui/material'

import { normalizeApiError } from '../api/errors'

type ApiErrorAlertProps = {
  error: unknown
  onRetry?: () => void
}

export function ApiErrorAlert({ error, onRetry }: ApiErrorAlertProps) {
  const normalized = normalizeApiError(error)
  const regenerateRequired =
    normalized.code === 'invalid_request'
    && /old-format|regenerate required|combine_constraint_miners/i.test(normalized.message)

  return (
    <Alert
      severity={normalized.status === 404 ? 'warning' : 'error'}
      role="alert"
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        ) : null
      }
    >
      <AlertTitle>{regenerateRequired ? 'Regenerate required' : normalized.title}</AlertTitle>
      <Stack spacing={0.5}>
        {regenerateRequired ? (
          <Typography variant="body2">
            This run uses an old-format combination artifact. Regenerate the run with the current combiner before using typed Combination or HITL review APIs.
          </Typography>
        ) : null}
        <Typography variant="body2">{normalized.message}</Typography>
        {normalized.status ? (
          <Typography variant="caption" color="text.secondary">
            {normalized.code} · HTTP {normalized.status}
          </Typography>
        ) : null}
      </Stack>
    </Alert>
  )
}
