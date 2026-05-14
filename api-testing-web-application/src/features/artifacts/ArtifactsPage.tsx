import { useMemo, useState } from 'react'
import {
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'

import type { ArtifactContentResponse } from '../../shared/api/generated/model'
import { formatBytes, formatDateTime } from '../../shared/lib/format'
import { stringifySafe } from '../../shared/lib/json'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { useArtifactContent, useArtifacts } from './api'
import { CodeViewerLazy, DiffViewerLazy } from './CodeViewerLazy'

export type ArtifactsPageSearch = {
  artifactId?: string
  compare?: boolean
  raw?: boolean
}

type ArtifactsPageProps = {
  runName: string
  search: ArtifactsPageSearch
}

function contentKind(content: ArtifactContentResponse['content']) {
  return 'content_kind' in content ? content.content_kind ?? 'summary' : 'summary'
}

function viewerLanguage(kind: string | undefined, mediaType: string) {
  if (kind === 'raw_json' || mediaType.includes('json')) return 'json'
  if (kind === 'raw_csv' || mediaType.includes('csv')) return 'csv'
  return 'text'
}

function contentValue(content: ArtifactContentResponse['content']) {
  if ('value' in content) return stringifySafe(content.value)
  if ('text' in content) return content.text
  return stringifySafe(content)
}

function CsvPreviewTable({ rows }: { rows: Array<Record<string, string>> }) {
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))

  if (rows.length === 0 || columns.length === 0) {
    return (
      <Typography color="text.secondary" variant="body2">
        No CSV rows available.
      </Typography>
    )
  }

  return (
    <TableContainer sx={{ border: '1px solid', borderColor: 'divider', maxHeight: 420 }}>
      <Table aria-label="CSV preview" size="small" stickyHeader>
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={column} sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                {column}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {columns.map((column) => (
                <TableCell key={column} sx={{ maxWidth: 320, verticalAlign: 'top' }}>
                  <Typography
                    component="span"
                    sx={{
                      display: 'block',
                      overflowWrap: 'anywhere',
                      whiteSpace: 'normal',
                    }}
                    variant="body2"
                  >
                    {row[column] ?? ''}
                  </Typography>
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function ArtifactContentPanel({ content }: { content: ArtifactContentResponse }) {
  const kind = contentKind(content.content)
  const value = contentValue(content.content)

  return (
    <Stack spacing={2}>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Chip label={kind} size="small" />
        <Chip label={content.raw ? 'raw' : 'summary'} size="small" variant="outlined" />
        <Chip label={content.metadata.raw_policy} size="small" variant="outlined" />
      </Stack>
      {content.raw && kind === 'raw_csv' && 'rows' in content.content ? (
        <CsvPreviewTable rows={content.content.rows} />
      ) : content.raw ? (
        <CodeViewerLazy
          language={viewerLanguage(kind, content.metadata.media_type)}
          value={value}
        />
      ) : (
        <JsonBlock value={content.content} />
      )}
    </Stack>
  )
}

export function ArtifactsPage({ runName, search }: ArtifactsPageProps) {
  const [exportOpen, setExportOpen] = useState(false)
  const artifactsQuery = useArtifacts(runName)
  const defaultArtifactId = artifactsQuery.data?.artifacts[0]?.artifact_id
  const [selectedArtifactId, setSelectedArtifactId] = useState(search.artifactId)
  const [raw, setRaw] = useState(Boolean(search.raw))
  const artifactId = selectedArtifactId ?? defaultArtifactId
  const compare = Boolean(search.compare)
  const contentQuery = useArtifactContent(
    runName,
    artifactId ?? '',
    { raw },
    { query: { enabled: Boolean(artifactId) && !compare } },
  )
  const summaryContentQuery = useArtifactContent(
    runName,
    artifactId ?? '',
    { raw: false },
    { query: { enabled: Boolean(artifactId) && compare } },
  )
  const rawContentQuery = useArtifactContent(
    runName,
    artifactId ?? '',
    { raw: true },
    { query: { enabled: Boolean(artifactId) && compare } },
  )

  const selectedArtifact = useMemo(
    () => artifactsQuery.data?.artifacts.find((artifact) => artifact.artifact_id === artifactId),
    [artifactId, artifactsQuery.data?.artifacts],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Button onClick={() => setExportOpen(true)} variant="outlined">
            Export snapshot
          </Button>
        }
        eyebrow="Artifact viewer"
        title="Artifacts"
        subtitle="Inspect summary, raw JSON/text/CSV, sanitized test cases, and sanitized HAR artifacts."
      />

      <QueryState
        empty={(artifactsQuery.data?.artifacts.length ?? 0) === 0}
        error={artifactsQuery.error}
        isError={artifactsQuery.isError}
        isLoading={artifactsQuery.isLoading}
        onRetry={() => void artifactsQuery.refetch()}
      >
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4, xl: 3 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography component="h2" sx={{ mb: 1 }} variant="h3">
                  Catalog
                </Typography>
                <List dense>
                  {(artifactsQuery.data?.artifacts ?? []).map((artifact) => (
                    <ListItemButton
                      key={artifact.artifact_id}
                      onClick={() => {
                        setSelectedArtifactId(artifact.artifact_id)
                        replaceSearchParams({ artifactId: artifact.artifact_id, raw })
                      }}
                      selected={artifact.artifact_id === artifactId}
                    >
                      <ListItemText
                        primary={artifact.artifact_id}
                        secondary={`${artifact.kind} · ${formatBytes(artifact.size_bytes)}`}
                      />
                    </ListItemButton>
                  ))}
                </List>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, md: 8, xl: 9 }}>
            <Card variant="outlined">
              <CardContent>
                <Stack spacing={2}>
                  <Stack
                    direction={{ xs: 'column', md: 'row' }}
                    spacing={1}
                    sx={{
                      alignItems: { xs: 'flex-start', md: 'center' },
                      justifyContent: 'space-between',
                    }}
                  >
                    <Stack spacing={0.5}>
                      <Typography component="h2" variant="h3">
                        {artifactId ?? 'No artifact selected'}
                      </Typography>
                      {selectedArtifact ? (
                        <Typography color="text.secondary" variant="caption">
                          {selectedArtifact.relative_path} · {selectedArtifact.media_type} · modified {formatDateTime(selectedArtifact.modified_at)}
                        </Typography>
                      ) : null}
                    </Stack>
                    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
                      <Typography variant="body2">Summary</Typography>
                      <Switch
                        checked={raw}
                        disabled={!selectedArtifact?.raw_supported}
                        onChange={(event) => {
                          setRaw(event.target.checked)
                          replaceSearchParams({ artifactId, compare: false, raw: event.target.checked })
                        }}
                        slotProps={{ input: { 'aria-label': 'Raw mode' } }}
                      />
                      <Typography variant="body2">Raw</Typography>
                      <Button
                        onClick={() => {
                          setRaw(false)
                          replaceSearchParams({ artifactId, compare: false, raw: false })
                        }}
                        size="small"
                        variant={!raw && !compare ? 'contained' : 'outlined'}
                      >
                        Summary
                      </Button>
                      <Button
                        onClick={() => {
                          setRaw(true)
                          replaceSearchParams({ artifactId, compare: false, raw: true })
                        }}
                        size="small"
                        variant={raw && !compare ? 'contained' : 'outlined'}
                      >
                        Raw
                      </Button>
                      <Button
                        disabled={!selectedArtifact?.raw_supported}
                        onClick={() => replaceSearchParams({ artifactId, compare: true, raw: false })}
                        size="small"
                        variant={compare ? 'contained' : 'outlined'}
                      >
                        Compare
                      </Button>
                    </Stack>
                  </Stack>

                  {compare ? (
                    <QueryState
                      empty={!summaryContentQuery.data || !rawContentQuery.data}
                      error={summaryContentQuery.error ?? rawContentQuery.error}
                      isError={summaryContentQuery.isError || rawContentQuery.isError}
                      isLoading={summaryContentQuery.isLoading || rawContentQuery.isLoading}
                      onRetry={() => {
                        void summaryContentQuery.refetch()
                        void rawContentQuery.refetch()
                      }}
                    >
                      {summaryContentQuery.data && rawContentQuery.data ? (
                        <Stack spacing={2}>
                          <Typography component="h3" variant="h3">
                            Compare summary and raw
                          </Typography>
                          <DiffViewerLazy
                            language={viewerLanguage(
                              contentKind(rawContentQuery.data.content),
                              rawContentQuery.data.metadata.media_type,
                            )}
                            modified={contentValue(rawContentQuery.data.content)}
                            original={stringifySafe(summaryContentQuery.data.content)}
                          />
                        </Stack>
                      ) : null}
                    </QueryState>
                  ) : (
                    <QueryState
                      empty={!contentQuery.data}
                      error={contentQuery.error}
                      isError={contentQuery.isError}
                      isLoading={contentQuery.isLoading}
                      onRetry={() => void contentQuery.refetch()}
                    >
                      {contentQuery.data ? <ArtifactContentPanel content={contentQuery.data} /> : null}
                    </QueryState>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </QueryState>
      <ExportSnapshotDialog
        data={{
          artifact: selectedArtifact,
          content: compare
            ? { raw: rawContentQuery.data, summary: summaryContentQuery.data }
            : contentQuery.data,
        }}
        filters={search}
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={`/runs/${encodeURIComponent(runName)}/artifacts`}
        title="Artifacts"
      />
    </Stack>
  )
}
