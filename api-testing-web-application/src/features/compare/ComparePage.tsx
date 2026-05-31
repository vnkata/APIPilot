import CompareArrowsIcon from '@mui/icons-material/CompareArrows'
import {
  Box,
  Button,
  Chip,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'

import { useArtifactContent, useArtifacts } from '../artifacts/api'
import { useRunSummary, useRuns } from '../runs/api'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ApiErrorAlert } from '../../shared/ui/ApiErrorAlert'
import { EmptyState } from '../../shared/ui/EmptyState'
import { PageHeader } from '../../shared/ui/PageHeader'
import { Panel } from '../../shared/ui/Panel'
import { QueryState } from '../../shared/ui/QueryState'

type CompareSearch = {
  artifactId?: string
  leftRun?: string
  raw: boolean
  rightRun?: string
}

type ComparePageProps = {
  search: CompareSearch
}

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2)
}

function SummaryPanel({ runName }: { runName?: string }) {
  const summaryQuery = useRunSummary(runName ?? '', {
    query: { enabled: Boolean(runName) },
  })

  if (!runName) return <EmptyState description="Choose a run to compare." title="No run selected" />

  return (
    <QueryState
      error={summaryQuery.error}
      isError={summaryQuery.isError}
      isLoading={summaryQuery.isLoading}
      onRetry={() => void summaryQuery.refetch()}
    >
      <Stack spacing={1.5}>
        <Typography sx={{ fontWeight: 800 }} variant="h3">
          {runName}
        </Typography>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Chip label={`${summaryQuery.data?.operation_count ?? 0} operations`} size="small" />
          <Chip label={`${summaryQuery.data?.static_constraint_count ?? 0} static constraints`} size="small" />
          <Chip label={`${summaryQuery.data?.dynamic_constraint_count ?? 0} dynamic constraints`} size="small" />
          <Chip label={`${summaryQuery.data?.test_case_count ?? 0} test cases`} size="small" />
          <Chip label={`${summaryQuery.data?.artifact_count ?? 0} artifacts`} size="small" />
        </Stack>
      </Stack>
    </QueryState>
  )
}

function ArtifactContentPanel({
  artifactId,
  raw,
  runName,
}: {
  artifactId?: string
  raw: boolean
  runName?: string
}) {
  const contentQuery = useArtifactContent(runName ?? '', artifactId ?? '', { raw }, {
    query: { enabled: Boolean(runName && artifactId) },
  })

  if (!runName || !artifactId) {
    return <EmptyState description="Pick a run and artifact to inspect content." title="No artifact selected" />
  }

  return (
    <QueryState
      error={contentQuery.error}
      isError={contentQuery.isError}
      isLoading={contentQuery.isLoading}
      onRetry={() => void contentQuery.refetch()}
    >
      <Box
        aria-label={`${runName} artifact content`}
        component="pre"
        sx={(theme) => ({
          bgcolor: theme.palette.background.default,
          border: '1px solid',
          borderColor: theme.apiTesting.border.default,
          borderRadius: 1,
          fontSize: 12,
          lineHeight: 1.6,
          maxHeight: 420,
          overflow: 'auto',
          p: 2,
          whiteSpace: 'pre-wrap',
        })}
      >
        {formatJson(contentQuery.data?.content)}
      </Box>
    </QueryState>
  )
}

export function ComparePage({ search }: ComparePageProps) {
  const runsQuery = useRuns()
  const leftArtifactsQuery = useArtifacts(search.leftRun ?? '', {
    query: { enabled: Boolean(search.leftRun) },
  })
  const rightArtifactsQuery = useArtifacts(search.rightRun ?? '', {
    query: { enabled: Boolean(search.rightRun) },
  })
  const runNames = runsQuery.data?.runs.map((run) => run.run_name) ?? []
  const artifactOptions = [
    ...(leftArtifactsQuery.data?.artifacts ?? []),
    ...(rightArtifactsQuery.data?.artifacts ?? []),
  ]
    .map((artifact) => artifact.artifact_id)
    .filter((artifactId, index, all) => all.indexOf(artifactId) === index)
    .sort()

  const selectedArtifactId = search.artifactId ?? artifactOptions[0]

  return (
    <Stack spacing={3}>
      <PageHeader
        eyebrow="Investigation"
        title="Compare runs"
        subtitle="Review run summaries and inspect the same artifact across two local APIPilot runs."
        actions={
          search.leftRun ? (
            <Button
              href={`/runs/${encodeURIComponent(search.leftRun)}`}
              startIcon={<CompareArrowsIcon />}
              variant="outlined"
            >
              Open left run
            </Button>
          ) : undefined
        }
      />

      {runsQuery.isError ? <ApiErrorAlert error={runsQuery.error} onRetry={() => void runsQuery.refetch()} /> : null}

      <Panel>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              fullWidth
              label="Left run"
              onChange={(event) => replaceSearchParams({ leftRun: event.target.value })}
              select
              value={search.leftRun ?? ''}
            >
              {runNames.map((runName) => (
                <MenuItem key={runName} value={runName}>
                  {runName}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              fullWidth
              label="Right run"
              onChange={(event) => replaceSearchParams({ rightRun: event.target.value })}
              select
              value={search.rightRun ?? ''}
            >
              {runNames.map((runName) => (
                <MenuItem key={runName} value={runName}>
                  {runName}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              fullWidth
              label="Artifact"
              onChange={(event) => replaceSearchParams({ artifactId: event.target.value })}
              select
              value={selectedArtifactId ?? ''}
            >
              {artifactOptions.map((artifactId) => (
                <MenuItem key={artifactId} value={artifactId}>
                  {artifactId}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        </Grid>
        <FormControlLabel
          control={
            <Switch
              checked={search.raw}
              onChange={(event) => replaceSearchParams({ raw: event.target.checked })}
            />
          }
          label="Request raw artifact content"
          sx={{ mt: 2 }}
        />
      </Panel>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Panel>
            <SummaryPanel runName={search.leftRun} />
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Panel>
            <SummaryPanel runName={search.rightRun} />
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Panel>
            <ArtifactContentPanel artifactId={selectedArtifactId} raw={search.raw} runName={search.leftRun} />
          </Panel>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Panel>
            <ArtifactContentPanel artifactId={selectedArtifactId} raw={search.raw} runName={search.rightRun} />
          </Panel>
        </Grid>
      </Grid>
    </Stack>
  )
}
