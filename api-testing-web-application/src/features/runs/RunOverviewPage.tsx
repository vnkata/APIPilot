import { Box, Button, Card, CardContent, Chip, Divider, Grid, Stack, Typography } from '@mui/material'

import { encodeRoutePart, formatBytes, formatDateTime } from '../../shared/lib/format'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { AppLink } from '../../shared/ui/AppLink'
import { ApiErrorAlert } from '../../shared/ui/ApiErrorAlert'
import { EvidenceSummaryCard } from '../../shared/ui/EvidenceSummaryCard'
import { MetricCard } from '../../shared/ui/MetricCard'
import { PageHeader } from '../../shared/ui/PageHeader'
import { PageSkeleton } from '../../shared/ui/PageSkeleton'
import { QueryState } from '../../shared/ui/QueryState'
import { StatusSignalStrip } from '../../shared/ui/StatusSignalStrip'
import { TriageMetricCard } from '../../shared/ui/TriageMetricCard'
import { ViewModeToggle } from '../../shared/ui/ViewModeToggle'
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
  search?: RunOverviewPageSearch
}

export type RunOverviewPageSearch = {
  overviewView?: 'classic' | 'command'
}

function statusChartData(statusCounts: Record<string, number> | undefined) {
  return Object.entries(statusCounts ?? {}).map(([status, count]) => ({ count, status }))
}

export function RunOverviewPage({ runName, search }: RunOverviewPageProps) {
  return <RunOverviewPageContent runName={runName} search={search ?? { overviewView: 'classic' }} />
}

export function RunOverviewPageContent({ runName, search }: RunOverviewPageProps) {
  const metadataQuery = useRunMetadata(runName, { query: { retry: false } })
  const summaryQuery = useRunSummary(runName, { query: { retry: false } })
  const operationsQuery = useRunOperations(runName)
  const artifactsQuery = useRunArtifacts(runName)
  const sessionsQuery = useRunHarSessions(runName)
  const overviewView = search?.overviewView ?? 'classic'
  const encodedRunName = encodeRoutePart(runName)

  if (metadataQuery.isLoading || summaryQuery.isLoading) return <PageSkeleton />
  if (metadataQuery.isError) return <ApiErrorAlert error={metadataQuery.error} onRetry={() => void metadataQuery.refetch()} />

  const failureOperations =
    operationsQuery.data?.operations.filter((operation) =>
      operation.response_statuses.some((status) => /^[45]/.test(status)),
    ).length ?? 0
  const totalConstraints = (summaryQuery.data?.static_constraint_count ?? 0) + (summaryQuery.data?.dynamic_constraint_count ?? 0)
  const artifactCount = artifactsQuery.data?.artifacts.length ?? summaryQuery.data?.artifact_count ?? 0
  const healthTone = failureOperations > 0 ? 'danger' : totalConstraints > 0 ? 'warning' : 'success'
  const headerActions = (
    <ViewModeToggle
      ariaLabel="Overview view mode"
      onChange={(value) => replaceSearchParams({ overviewView: value })}
      options={[
        { description: 'Current overview cards and artifact availability.', label: 'Classic', value: 'classic' },
        { description: 'QA triage command center.', label: 'Command', value: 'command' },
      ]}
      value={overviewView}
    />
  )

  if (overviewView === 'command') {
    return (
      <Stack spacing={2}>
        <PageHeader
          actions={headerActions}
          eyebrow="Run overview"
          subtitle={
            metadataQuery.data
              ? `${metadataQuery.data.artifact_count} artifacts · ${formatBytes(metadataQuery.data.size_bytes)} · modified ${formatDateTime(metadataQuery.data.modified_at)}`
              : 'Run metadata unavailable'
          }
          title="QA Mission Control"
        />

        <QueryState
          empty={!summaryQuery.data}
          error={summaryQuery.error}
          isError={summaryQuery.isError}
          isLoading={summaryQuery.isLoading}
          onRetry={() => void summaryQuery.refetch()}
        >
          <Card variant="outlined">
            <CardContent>
              <Stack spacing={2}>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' } }}>
                  <Stack spacing={0.5} sx={{ flex: 1, minWidth: 0 }}>
                    <Typography component="h2" variant="h2">
                      {runName}
                    </Typography>
                    <Typography color="text.secondary" variant="body2">
                      Fast triage surface for failures, oracle readiness, graph evidence, and artifact inspection.
                    </Typography>
                  </Stack>
                  <StatusSignalStrip
                    ariaLabel="Run health signals"
                    signals={[
                      { label: 'Failure signal', tone: failureOperations > 0 ? 'danger' : 'success', value: failureOperations },
                      { label: 'Constraints', tone: totalConstraints > 0 ? 'warning' : 'neutral', value: totalConstraints },
                      { label: 'Artifacts', tone: artifactCount > 0 ? 'success' : 'neutral', value: artifactCount },
                    ]}
                  />
                </Stack>

                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                    <TriageMetricCard
                      caption="Failure signal across operation response statuses"
                      label="Failure signal"
                      tone={healthTone}
                      value={failureOperations}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                    <TriageMetricCard
                      caption={`${operationsQuery.data?.operations.length ?? summaryQuery.data?.operation_count ?? 0} operations loaded`}
                      label="Operations"
                      tone="neutral"
                      value={summaryQuery.data?.operation_count ?? 0}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                    <TriageMetricCard
                      caption={`${summaryQuery.data?.static_constraint_count ?? 0} static / ${summaryQuery.data?.dynamic_constraint_count ?? 0} dynamic`}
                      label="Oracle coverage"
                      tone={totalConstraints > 0 ? 'warning' : 'neutral'}
                      value={totalConstraints}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
                    <TriageMetricCard
                      caption={`${sessionsQuery.data?.sessions.length ?? summaryQuery.data?.har_session_count ?? 0} HAR sessions`}
                      label="Test evidence"
                      tone="success"
                      value={summaryQuery.data?.test_case_count ?? 0}
                    />
                  </Grid>
                </Grid>
              </Stack>
            </CardContent>
          </Card>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 7 }}>
              <Card variant="outlined" sx={{ height: '100%' }}>
                <CardContent>
                  <Typography component="h2" sx={{ mb: 2 }} variant="h3">
                    Status distribution
                  </Typography>
                  <Box sx={{ height: 280 }}>
                    <StatusBarChart data={statusChartData(summaryQuery.data?.report_status_counts)} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, lg: 5 }}>
              <Card variant="outlined" sx={{ height: '100%' }}>
                <CardContent>
                  <Stack spacing={2}>
                    <Typography component="h2" variant="h3">
                      Next best inspection
                    </Typography>
                    <EvidenceSummaryCard
                      description="Start with operations that carry failure statuses, constraints, graph edges, or invariant evidence."
                      title={
                        <AppLink href={`/runs/${encodedRunName}/operations?operationsView=canvas&hasFailures=true`}>
                          Review risky operations
                        </AppLink>
                      }
                      tone={failureOperations > 0 ? 'danger' : 'neutral'}
                    />
                    <Divider />
                    <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                      <Button href={`/runs/${encodedRunName}/constraints?constraintsView=matrix`} size="small" variant="outlined">
                        Constraint matrix
                      </Button>
                      <Button href={`/runs/${encodedRunName}/graph?graphView=journey&graphTab=sequences`} size="small" variant="outlined">
                        Dependency journey
                      </Button>
                      <Button href={`/runs/${encodedRunName}/artifacts?artifactsView=workbench`} size="small" variant="outlined">
                        Artifact workbench
                      </Button>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </QueryState>
      </Stack>
    )
  }

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={headerActions}
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
