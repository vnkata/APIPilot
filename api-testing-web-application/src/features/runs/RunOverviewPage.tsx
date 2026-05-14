import { Box, Chip, Grid, Stack, Typography } from '@mui/material'

import { formatBytes, formatDateTime } from '../../shared/lib/format'
import { ApiErrorAlert } from '../../shared/ui/ApiErrorAlert'
import { MetricCard } from '../../shared/ui/MetricCard'
import { PageHeader } from '../../shared/ui/PageHeader'
import { PageSkeleton } from '../../shared/ui/PageSkeleton'
import { QueryState } from '../../shared/ui/QueryState'
import { StatusBarChart } from '../reports/StatusBarChart'
import {
  useRunArtifacts,
  useRunHarSessions,
  useRunMetadata,
  useRunOperations,
  useRunSummary,
} from './api'

type RunOverviewPageProps = {
  runName: string
}

function statusChartData(statusCounts: Record<string, number> | undefined) {
  return Object.entries(statusCounts ?? {}).map(([status, count]) => ({ count, status }))
}

export function RunOverviewPage({ runName }: RunOverviewPageProps) {
  const metadataQuery = useRunMetadata(runName, { query: { retry: false } })
  const summaryQuery = useRunSummary(runName, { query: { retry: false } })
  const operationsQuery = useRunOperations(runName)
  const artifactsQuery = useRunArtifacts(runName)
  const sessionsQuery = useRunHarSessions(runName)

  if (metadataQuery.isLoading || summaryQuery.isLoading) return <PageSkeleton />
  if (metadataQuery.isError) return <ApiErrorAlert error={metadataQuery.error} onRetry={() => void metadataQuery.refetch()} />

  return (
    <Stack spacing={2}>
      <PageHeader
        eyebrow="Run overview"
        title={runName}
        subtitle={
          metadataQuery.data
            ? `${metadataQuery.data.artifact_count} artifacts · ${formatBytes(metadataQuery.data.size_bytes)} · modified ${formatDateTime(metadataQuery.data.modified_at)}`
            : 'Run metadata unavailable'
        }
      />

      <QueryState
        empty={!summaryQuery.data}
        error={summaryQuery.error}
        isError={summaryQuery.isError}
        isLoading={summaryQuery.isLoading}
        onRetry={() => void summaryQuery.refetch()}
      >
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <MetricCard
              caption={`${operationsQuery.data?.operations.length ?? summaryQuery.data?.operation_count ?? 0} loaded`}
              label="Operations"
              value={summaryQuery.data?.operation_count ?? 0}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <MetricCard label="Artifacts" value={summaryQuery.data?.artifact_count ?? 0} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <MetricCard label="Constraints" value={(summaryQuery.data?.static_constraint_count ?? 0) + (summaryQuery.data?.dynamic_constraint_count ?? 0)} />
          </Grid>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <MetricCard
              caption={`${sessionsQuery.data?.sessions.length ?? summaryQuery.data?.har_session_count ?? 0} HAR sessions`}
              label="Test cases"
              value={summaryQuery.data?.test_case_count ?? 0}
            />
          </Grid>
        </Grid>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, lg: 7 }}>
            <Box
              sx={{
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                height: 320,
                p: 2,
              }}
            >
              <Typography component="h2" sx={{ mb: 2 }} variant="h3">
                Status distribution
              </Typography>
              <StatusBarChart data={statusChartData(summaryQuery.data?.report_status_counts)} />
            </Box>
          </Grid>
          <Grid size={{ xs: 12, lg: 5 }}>
            <Box
              sx={{
                bgcolor: 'background.paper',
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                p: 2,
              }}
            >
              <Typography component="h2" sx={{ mb: 2 }} variant="h3">
                Artifact availability
              </Typography>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                {Object.entries(summaryQuery.data?.available_artifacts ?? {}).map(([key, available]) => (
                  <Chip
                    color={available ? 'success' : 'default'}
                    key={key}
                    label={key}
                    size="small"
                    variant={available ? 'filled' : 'outlined'}
                  />
                ))}
              </Stack>
              <Typography color="text.secondary" sx={{ mt: 2 }} variant="body2">
                Catalog query loaded {artifactsQuery.data?.artifacts.length ?? 0} artifact descriptors.
              </Typography>
            </Box>
          </Grid>
        </Grid>
      </QueryState>
    </Stack>
  )
}
