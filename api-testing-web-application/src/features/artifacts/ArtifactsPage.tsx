import { useMemo, useState } from 'react'
import {
  Box,
  Button,
  Chip,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material'

import type { ArtifactContentResponse } from '../../shared/api/generated/model'
import { formatBytes, formatDateTime } from '../../shared/lib/format'
import { stringifySafe } from '../../shared/lib/json'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { PageHeader } from '../../shared/ui/PageHeader'
import { Panel } from '../../shared/ui/Panel'
import { QueryState } from '../../shared/ui/QueryState'
import { ResponsiveWorkbenchLayout } from '../../shared/ui/ResponsiveWorkbenchLayout'
import { SensitiveDataNotice } from '../../shared/ui/SensitiveDataNotice'
import { ViewModeToggle } from '../../shared/ui/ViewModeToggle'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
import { useArtifactContent, useArtifacts } from './api'
import { CodeViewerLazy, DiffViewerLazy } from './CodeViewerLazy'

type ArtifactMode = 'compare' | 'raw' | 'summary'

export type ArtifactsPageSearch = {
  artifactId?: string
  artifactMode?: ArtifactMode
  artifactsView?: 'classic' | 'workbench'
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

function resolveArtifactMode(search: ArtifactsPageSearch): ArtifactMode {
  if (search.artifactMode) return search.artifactMode
  if (search.compare) return 'compare'
  if (search.raw) return 'raw'
  return 'summary'
}

function replaceArtifactSearch(updates: Record<string, boolean | string | undefined>) {
  replaceSearchParams({
    ...updates,
    compare: undefined,
    raw: undefined,
  })
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
  const [catalogQuery, setCatalogQuery] = useState('')
  const [kindFilter, setKindFilter] = useState('')
  const [policyFilter, setPolicyFilter] = useState('')
  const artifactsQuery = useArtifacts(runName)
  const artifactsView = search.artifactsView ?? 'workbench'
  const defaultArtifactId = artifactsQuery.data?.artifacts[0]?.artifact_id
  const artifactId = search.artifactId ?? defaultArtifactId
  const selectedArtifact = useMemo(
    () => artifactsQuery.data?.artifacts.find((artifact) => artifact.artifact_id === artifactId),
    [artifactId, artifactsQuery.data?.artifacts],
  )
  const requestedMode = resolveArtifactMode(search)
  const rawSupported = selectedArtifact?.raw_supported ?? true
  const artifactMode: ArtifactMode = rawSupported || requestedMode === 'summary' ? requestedMode : 'summary'
  const raw = artifactMode === 'raw'
  const compare = artifactMode === 'compare'
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

  const artifacts = useMemo(
    () => artifactsQuery.data?.artifacts ?? [],
    [artifactsQuery.data?.artifacts],
  )
  const kindOptions = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.kind))).sort(),
    [artifacts],
  )
  const policyOptions = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.raw_policy))).sort(),
    [artifacts],
  )
  const filteredArtifacts = useMemo(
    () =>
      artifacts.filter((artifact) => {
        const query = catalogQuery.trim().toLowerCase()
        const matchesQuery =
          query.length === 0 ||
          [
            artifact.artifact_id,
            artifact.kind,
            artifact.media_type,
            artifact.raw_policy,
            artifact.relative_path,
          ].some((value) => value.toLowerCase().includes(query))

        return (
          matchesQuery &&
          (!kindFilter || artifact.kind === kindFilter) &&
          (!policyFilter || artifact.raw_policy === policyFilter)
        )
      }),
    [artifacts, catalogQuery, kindFilter, policyFilter],
  )

  const catalogPanel = (
    <Panel
      subtitle={`${filteredArtifacts.length} of ${artifacts.length} artifacts visible`}
      title="Catalog"
      {...tourAnchor(TOUR_ANCHORS.artifactsCatalog)}
    >
      <Stack spacing={1.5}>
        <TextField
          fullWidth
          label="Search catalog"
          onChange={(event) => setCatalogQuery(event.target.value)}
          size="small"
          value={catalogQuery}
        />
        <Stack direction={{ xs: 'column', sm: 'row', md: 'column' }} spacing={1}>
          <TextField
            label="Kind"
            onChange={(event) => setKindFilter(event.target.value)}
            select
            size="small"
            value={kindFilter}
          >
            <MenuItem value="">All kinds</MenuItem>
            {kindOptions.map((kind) => (
              <MenuItem key={kind} value={kind}>
                {kind}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Raw policy"
            onChange={(event) => setPolicyFilter(event.target.value)}
            select
            size="small"
            value={policyFilter}
          >
            <MenuItem value="">All policies</MenuItem>
            {policyOptions.map((policy) => (
              <MenuItem key={policy} value={policy}>
                {policy}
              </MenuItem>
            ))}
          </TextField>
        </Stack>
        <List dense>
          {filteredArtifacts.map((artifact) => {
            const nextMode = artifact.raw_supported ? artifactMode : 'summary'
            return (
              <ListItemButton
                key={artifact.artifact_id}
                onClick={() => {
                  replaceArtifactSearch({ artifactId: artifact.artifact_id, artifactMode: nextMode })
                }}
                selected={artifact.artifact_id === artifactId}
              >
                <ListItemText
                  primary={artifact.artifact_id}
                  secondary={
                    artifactsView === 'workbench'
                      ? `${artifact.kind} · ${formatBytes(artifact.size_bytes)} · Raw policy: ${artifact.raw_policy}`
                      : `${artifact.kind} · ${formatBytes(artifact.size_bytes)}`
                  }
                />
              </ListItemButton>
            )
          })}
        </List>
        {filteredArtifacts.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            No artifacts match the current catalog filters.
          </Typography>
        ) : null}
      </Stack>
    </Panel>
  )

  const detailPanel = (
    <Panel {...tourAnchor(TOUR_ANCHORS.artifactsDetail)}>
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
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', flexWrap: 'wrap' }}>
            <ToggleButtonGroup
              aria-label="Artifact content mode"
              exclusive
              onChange={(_, value: ArtifactMode | null) => {
                if (value) replaceArtifactSearch({ artifactId, artifactMode: value })
              }}
              size="small"
              value={artifactMode}
            >
              <ToggleButton value="summary">Summary</ToggleButton>
              <ToggleButton disabled={!selectedArtifact?.raw_supported} value="raw">
                Raw
              </ToggleButton>
              <ToggleButton disabled={!selectedArtifact?.raw_supported} value="compare">
                Compare
              </ToggleButton>
            </ToggleButtonGroup>
          </Stack>
        </Stack>

          {artifactsView === 'workbench' && selectedArtifact ? (
            <Box
              sx={(theme) => ({
                bgcolor: theme.apiTesting.surface.overlay,
                border: '1px solid',
                borderColor: theme.apiTesting.border.default,
                borderRadius: 1.25,
                p: 1.5,
                position: { md: 'sticky' },
                top: { md: 72 },
                zIndex: 1,
              })}
            >
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Chip label={`Raw policy: ${selectedArtifact.raw_policy}`} size="small" />
                <Chip label={selectedArtifact.media_type} size="small" variant="outlined" />
                <Chip label={formatBytes(selectedArtifact.size_bytes)} size="small" variant="outlined" />
                <Chip label={selectedArtifact.summary_supported ? 'Summary supported' : 'Summary missing'} size="small" variant="outlined" />
                <Chip label={selectedArtifact.raw_supported ? 'Raw supported' : 'Raw missing'} size="small" variant="outlined" />
              </Stack>
            </Box>
          ) : null}

          {requestedMode !== 'summary' && !rawSupported ? (
            <SensitiveDataNotice severity="info" title="Raw content unavailable">
              This artifact does not expose raw content. APIPilot is showing the summary view while preserving the selected artifact.
            </SensitiveDataNotice>
          ) : null}

          {raw || compare ? <SensitiveDataNotice /> : null}

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
    </Panel>
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', justifyContent: { xs: 'flex-start', md: 'flex-end' } }}>
            <ViewModeToggle
              ariaLabel="Artifacts view mode"
              onChange={(value) => replaceArtifactSearch({ artifactsView: value })}
              options={[
                { description: 'Current catalog and inspector.', label: 'Classic', value: 'classic' },
                { description: 'Metadata-rich artifact inspection workbench.', label: 'Workbench', value: 'workbench' },
              ]}
              value={artifactsView}
            />
            <Button onClick={() => setExportOpen(true)} variant="outlined">
              Export snapshot
            </Button>
          </Stack>
        }
        eyebrow="Artifact viewer"
        title={artifactsView === 'workbench' ? 'Artifact Workbench' : 'Artifacts'}
        subtitle="Inspect summary, raw JSON/text/CSV, sanitized test cases, and sanitized HAR artifacts."
        {...tourAnchor(TOUR_ANCHORS.artifactsHeader)}
      />

      <QueryState
        empty={(artifactsQuery.data?.artifacts.length ?? 0) === 0}
        error={artifactsQuery.error}
        isError={artifactsQuery.isError}
        isLoading={artifactsQuery.isLoading}
        onRetry={() => void artifactsQuery.refetch()}
      >
        {artifactsView === 'workbench' ? (
          <ResponsiveWorkbenchLayout detail={detailPanel} sidebar={catalogPanel} />
        ) : (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4, xl: 3 }}>{catalogPanel}</Grid>
            <Grid size={{ xs: 12, md: 8, xl: 9 }}>{detailPanel}</Grid>
          </Grid>
        )}
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
