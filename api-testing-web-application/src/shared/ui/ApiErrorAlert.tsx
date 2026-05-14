import { Alert, AlertTitle, Button, Stack, Typography } from '@mui/material'

import { normalizeApiError } from '../api/errors'

type ApiErrorAlertProps = {
  error: unknown
  onRetry?: () => void
}

export function ApiErrorAlert({ error, onRetry }: ApiErrorAlertProps) {
  const normalized = normalizeApiError(error)

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
      <AlertTitle>{normalized.title}</AlertTitle>
      <Stack spacing={0.5}>
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
