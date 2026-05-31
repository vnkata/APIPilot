import CompareArrowsIcon from '@mui/icons-material/CompareArrows'
import {
  Box,
  Button,
  Chip,
  Divider,
  FormControlLabel,
  Grid,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'

import { useArtifactContent, useArtifacts } from '../artifacts/api'
import { DiffViewerLazy } from '../artifacts/CodeViewerLazy'
import { useRunSummary, useRuns } from '../runs/api'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { stringifySafe } from '../../shared/lib/json'
import { ApiErrorAlert } from '../../shared/ui/ApiErrorAlert'
import { EmptyState } from '../../shared/ui/EmptyState'
import { PageHeader } from '../../shared/ui/PageHeader'
import { Panel } from '../../shared/ui/Panel'
import { QueryState } from '../../shared/ui/QueryState'
import {
  buildArtifactMetadataDiff,
  buildJsonDiff,
  extractComparableContent,
} from './compareDiff'
import type { ArtifactCatalogResponse, ArtifactContentResponse } from '../../shared/api/generated/model'

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

function diffLanguage(mediaType?: string) {
  if (mediaType?.includes('json')) return 'json'
  if (mediaType?.includes('csv')) return 'csv'
  return 'text'
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

function MetadataDiffPanel({
  leftArtifact,
  rightArtifact,
}: {
  leftArtifact?: ArtifactCatalogResponse['artifacts'][number]
  rightArtifact?: ArtifactCatalogResponse['artifacts'][number]
}) {
  const diff = buildArtifactMetadataDiff(leftArtifact, rightArtifact)
  const statusLabel =
    diff.status === 'match'
      ? 'Present on both sides'
      : diff.status === 'left-only'
        ? 'Missing on right'
        : diff.status === 'right-only'
          ? 'Missing on left'
          : `${diff.changed.length} metadata changes`

  return (
    <Panel title="Artifact metadata diff" subtitle="Presence, size, media type, raw policy, and capability deltas.">
      <Stack spacing={1.5}>
        <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Chip color={diff.status === 'match' ? 'success' : 'warning'} label={statusLabel} size="small" />
          {leftArtifact ? <Chip label={`Left size ${leftArtifact.size_bytes} bytes`} size="small" variant="outlined" /> : null}
          {rightArtifact ? <Chip label={`Right size ${rightArtifact.size_bytes} bytes`} size="small" variant="outlined" /> : null}
        </Stack>
        {diff.changed.length > 0 ? (
          <Stack divider={<Divider flexItem />} spacing={1}>
            {diff.changed.map((item) => (
              <Grid key={String(item.field)} container spacing={1}>
                <Grid size={{ xs: 12, md: 3 }}>
                  <Typography sx={{ fontWeight: 800 }} variant="body2">
                    {String(item.field)}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, md: 4.5 }}>
                  <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="body2">
                    {String(item.left)}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, md: 4.5 }}>
                  <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="body2">
                    {String(item.right)}
                  </Typography>
                </Grid>
              </Grid>
            ))}
          </Stack>
        ) : (
          <Typography color="text.secondary" variant="body2">
            No artifact metadata deltas for the current selection.
          </Typography>
        )}
      </Stack>
    </Panel>
  )
}

function ContentDiffPanel({
  leftContent,
  raw,
  rightContent,
}: {
  leftContent?: ArtifactContentResponse
  raw: boolean
  rightContent?: ArtifactContentResponse
}) {
  const leftComparable = extractComparableContent(leftContent)
  const rightComparable = extractComparableContent(rightContent)
  const jsonDiff = buildJsonDiff(leftComparable, rightComparable)

  return (
    <Panel
      title={raw ? 'Raw artifact diff' : 'JSON structural diff'}
      subtitle={raw ? 'Monaco is loaded only for raw/text diff mode.' : 'Added, removed, and changed JSON-like paths.'}
    >
      {!leftContent || !rightContent ? (
        <EmptyState description="Choose two runs and an artifact to compare content." title="No comparable content" />
      ) : raw ? (
        <DiffViewerLazy
          language={diffLanguage(rightContent.metadata.media_type || leftContent.metadata.media_type)}
          modified={typeof rightComparable === 'string' ? rightComparable : stringifySafe(rightComparable)}
          original={typeof leftComparable === 'string' ? leftComparable : stringifySafe(leftComparable)}
        />
      ) : (
        <Stack spacing={1.5}>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Chip label={`${jsonDiff.summary.added} added`} size="small" />
            <Chip label={`${jsonDiff.summary.removed} removed`} size="small" />
            <Chip label={`${jsonDiff.summary.changed} changed`} size="small" />
          </Stack>
          {jsonDiff.items.length > 0 ? (
            <Stack divider={<Divider flexItem />} spacing={1}>
              {jsonDiff.items.slice(0, 50).map((item) => (
                <Grid key={`${item.kind}:${item.path}`} container spacing={1}>
                  <Grid size={{ xs: 12, md: 2 }}>
                    <Chip
                      color={item.kind === 'changed' ? 'warning' : item.kind === 'added' ? 'success' : 'default'}
                      label={item.kind}
                      size="small"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 4 }}>
                    <Typography sx={{ fontFamily: 'monospace', overflowWrap: 'anywhere' }} variant="body2">
                      {item.path}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="caption">
                      {item.left === undefined ? '' : stringifySafe(item.left)}
                    </Typography>
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="caption">
                      {item.right === undefined ? '' : stringifySafe(item.right)}
                    </Typography>
                  </Grid>
                </Grid>
              ))}
            </Stack>
          ) : (
            <Typography color="text.secondary" variant="body2">
              No structural content deltas for the current selection.
            </Typography>
          )}
        </Stack>
      )}
    </Panel>
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
  const leftArtifact = leftArtifactsQuery.data?.artifacts.find((artifact) => artifact.artifact_id === selectedArtifactId)
  const rightArtifact = rightArtifactsQuery.data?.artifacts.find((artifact) => artifact.artifact_id === selectedArtifactId)
  const leftContentQuery = useArtifactContent(search.leftRun ?? '', selectedArtifactId ?? '', { raw: search.raw }, {
    query: { enabled: Boolean(search.leftRun && selectedArtifactId) },
  })
  const rightContentQuery = useArtifactContent(search.rightRun ?? '', selectedArtifactId ?? '', { raw: search.raw }, {
    query: { enabled: Boolean(search.rightRun && selectedArtifactId) },
  })

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
        <Grid size={{ xs: 12 }}>
          <MetadataDiffPanel leftArtifact={leftArtifact} rightArtifact={rightArtifact} />
        </Grid>
        <Grid size={{ xs: 12 }}>
          <QueryState
            empty={!leftContentQuery.data || !rightContentQuery.data}
            error={leftContentQuery.error ?? rightContentQuery.error}
            isError={leftContentQuery.isError || rightContentQuery.isError}
            isLoading={leftContentQuery.isLoading || rightContentQuery.isLoading}
            onRetry={() => {
              void leftContentQuery.refetch()
              void rightContentQuery.refetch()
            }}
          >
            <ContentDiffPanel
              leftContent={leftContentQuery.data}
              raw={search.raw}
              rightContent={rightContentQuery.data}
            />
          </QueryState>
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
