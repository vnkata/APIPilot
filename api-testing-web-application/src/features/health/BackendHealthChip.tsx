import Chip from '@mui/material/Chip'

import { useBackendHealth } from './api'

export function BackendHealthChip() {
  const healthQuery = useBackendHealth({
    query: {
      refetchInterval: 60_000,
      retry: false,
      staleTime: 60_000,
    },
  })

  if (healthQuery.isLoading) {
    return <Chip color="default" label="Backend checking" size="small" variant="outlined" />
  }

  if (healthQuery.isError) {
    return <Chip color="error" label="Backend offline" size="small" variant="outlined" />
  }

  return (
    <Chip
      color="success"
      label={`Backend ${healthQuery.data?.status ?? 'ok'}`}
      size="small"
      variant="outlined"
    />
  )
}
