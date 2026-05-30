import { useMemo } from 'react'
import {
  Alert,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControlLabel,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  Switch,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'

import type { HarEntryResponse } from '../../shared/api/generated/model'
import { formatBytes, formatDateTime } from '../../shared/lib/format'
import { stringifySafe } from '../../shared/lib/json'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { HttpMethodBadge, StatusCodeBadge } from '../../shared/ui/SemanticBadges'
import { SensitiveDataNotice } from '../../shared/ui/SensitiveDataNotice'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
import { useHarEntries, useHarSessions } from './api'

export type HistoryPageSearch = {
  entryId?: string
  includeBody?: boolean
  limit: number
  offset: number
  sessionId?: string
}

type HistoryPageProps = {
  runName: string
  search: HistoryPageSearch
}

type HarEntryRow = HarEntryResponse & {
  id: string
}

function hasRedactionMarker(row: HarEntryRow) {
  const headers = `${stringifySafe(row.request_headers)} ${stringifySafe(row.response_headers)}`
  return headers.includes('<REDACTED>')
}

function HarEntryDetailDrawer({
  includeBody,
  row,
}: {
  includeBody: boolean
  row?: HarEntryRow
}) {
  const open = Boolean(row)

  function handleClose() {
    replaceSearchParams({ entryId: undefined })
  }

  return (
    <InvestigationDrawer
      ariaLabel="HAR entry detail"
      onClose={handleClose}
      open={open}
      subtitle={row?.entry_id}
      title="HAR entry detail"
      data-tour-anchor={TOUR_ANCHORS.historyDetail}
    >
      {row ? (
        <Stack spacing={2}>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <HttpMethodBadge method={row.request_method} />
            <StatusCodeBadge statusCode={row.response_status} />
            <Chip label={`${row.duration_ms ?? 0} ms`} variant="outlined" />
            {hasRedactionMarker(row) ? <Chip color="warning" label="<REDACTED>" /> : null}
          </Stack>
          <Typography color="text.secondary" sx={{ overflowWrap: 'anywhere' }} variant="body2">
            {row.request_url}
          </Typography>
          <Divider />
          <Typography component="h3" variant="subtitle2">
            Query parameters
          </Typography>
          <JsonBlock maxHeight={160} value={row.query_params} />
          <Typography component="h3" variant="subtitle2">
            Request headers
          </Typography>
          <JsonBlock maxHeight={180} value={row.request_headers} />
          <Typography component="h3" variant="subtitle2">
            Response headers
          </Typography>
          <JsonBlock maxHeight={180} value={row.response_headers} />
          {includeBody ? (
            <>
              <SensitiveDataNotice>
                Sanitized HAR bodies are visible for this entry. Redaction markers do not guarantee all payload context is safe to share.
              </SensitiveDataNotice>
              <Typography component="h3" variant="subtitle2">
                Request body
              </Typography>
              <JsonBlock maxHeight={180} value={row.request_body ?? null} />
              <Typography component="h3" variant="subtitle2">
                Response body
              </Typography>
              <JsonBlock maxHeight={220} value={row.response_body ?? null} />
            </>
          ) : (
            <Alert severity="info">Payload fields are hidden. Enable sanitized bodies to inspect them.</Alert>
          )}
        </Stack>
      ) : null}
    </InvestigationDrawer>
  )
}

export function HistoryPage({ runName, search }: HistoryPageProps) {
  const gridState = useUrlBackedGridState(search)
  const includeBody = Boolean(search.includeBody)
  const sessionsQuery = useHarSessions(runName)
  const sessionId = search.sessionId ?? sessionsQuery.data?.sessions[0]?.session_id
  const entriesQuery = useHarEntries(
    runName,
    sessionId ?? '',
    {
      include_body: includeBody,
      limit: search.limit,
      offset: search.offset,
    },
    { query: { enabled: Boolean(sessionId) } },
  )
  const rows: HarEntryRow[] = (entriesQuery.data?.items ?? []).map((item) => ({
    ...item,
    id: item.entry_id,
  }))
  const selectedEntry = rows.find((row) => row.id === search.entryId)
  const redactedCount = useMemo(
    () => rows.reduce((count, row) => count + (hasRedactionMarker(row) ? 1 : 0), 0),
    [rows],
  )
  const entryColumns = useMemo<GridColDef<HarEntryRow>[]>(
    () => [
      { field: 'entry_id', flex: 0.8, headerName: 'Entry', minWidth: 140 },
      {
        field: 'request_method',
        flex: 0.5,
        headerName: 'Method',
        minWidth: 112,
        renderCell: (params) => <HttpMethodBadge method={params.row.request_method} />,
      },
      { field: 'request_url', flex: 1.5, headerName: 'URL', minWidth: 260 },
      {
        field: 'response_status',
        flex: 0.6,
        headerName: 'Status',
        minWidth: 150,
        renderCell: (params) => <StatusCodeBadge statusCode={params.row.response_status} />,
        type: 'number',
      },
      { field: 'duration_ms', flex: 0.6, headerName: 'Duration ms', minWidth: 120, type: 'number' },
      {
        field: 'request_headers',
        flex: 1.2,
        headerName: 'Request headers',
        minWidth: 240,
        valueGetter: (_value, row) => stringifySafe(row.request_headers),
      },
      {
        field: 'response_headers',
        flex: 1.2,
        headerName: 'Response headers',
        minWidth: 240,
        valueGetter: (_value, row) => stringifySafe(row.response_headers),
      },
    ],
    [],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        eyebrow="HTTP history"
        title="HAR sessions"
        subtitle="Inspect sanitized request/response history entries captured by APIPilot."
        {...tourAnchor(TOUR_ANCHORS.historyHeader)}
      />

      <Alert severity="info">
        HAR bodies are omitted by default. Header redaction markers remain visible to support auditability.
      </Alert>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4, xl: 3 }}>
          <Card variant="outlined" {...tourAnchor(TOUR_ANCHORS.historySessions)}>
            <CardContent>
              <Typography component="h2" sx={{ mb: 1 }} variant="h3">
                Sessions
              </Typography>
              <QueryState
                empty={(sessionsQuery.data?.sessions.length ?? 0) === 0}
                error={sessionsQuery.error}
                isError={sessionsQuery.isError}
                isLoading={sessionsQuery.isLoading}
                onRetry={() => void sessionsQuery.refetch()}
              >
                <List dense>
                  {(sessionsQuery.data?.sessions ?? []).map((session) => (
                    <ListItemButton
                      key={session.session_id}
                      onClick={() => {
                        replaceSearchParams({
                          entryId: undefined,
                          offset: 0,
                          sessionId: session.session_id,
                        })
                      }}
                      selected={session.session_id === sessionId}
                    >
                      <ListItemText
                        primary={session.session_id}
                        secondary={`${session.entry_count} entries · ${formatBytes(session.size_bytes)} · ${formatDateTime(session.modified_at)}`}
                      />
                    </ListItemButton>
                  ))}
                </List>
              </QueryState>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 12, md: 8, xl: 9 }}>
          <Card variant="outlined" {...tourAnchor(TOUR_ANCHORS.historyResults)}>
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
                  <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                    <Chip label={sessionId ?? 'No session'} />
                    <Chip color="warning" label={`${redactedCount} redaction markers`} />
                    {rows.some(hasRedactionMarker) ? <Typography component="span">&lt;REDACTED&gt;</Typography> : null}
                  </Stack>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={includeBody}
                        onChange={(event) => {
                          replaceSearchParams({ includeBody: event.target.checked, sessionId })
                        }}
                      />
                    }
                    label="Include sanitized bodies"
                  />
                </Stack>
                <ActiveFilterChips
                  filters={[
                    { key: 'sessionId', label: 'Session', value: search.sessionId },
                    { key: 'entryId', label: 'Entry', value: search.entryId },
                    { key: 'includeBody', label: 'Bodies', value: search.includeBody ? 'included' : undefined },
                  ]}
                />
                {includeBody ? (
                  <SensitiveDataNotice>
                    Sanitized HAR bodies are included in this table and drawer. Keep exported evidence local unless reviewed.
                  </SensitiveDataNotice>
                ) : null}

                <QueryState
                  empty={rows.length === 0}
                  error={entriesQuery.error}
                  isError={entriesQuery.isError}
                  isLoading={entriesQuery.isLoading}
                  onRetry={() => void entriesQuery.refetch()}
                >
                  <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                    {rows.map((row) => (
                      <Chip
                        key={row.id}
                        label={row.entry_id}
                        onClick={() => replaceSearchParams({ entryId: row.id })}
                        size="small"
                      />
                    ))}
                  </Stack>
                  <ServerDataGridPanel
                    ariaLabel="HAR entries"
                    columns={entryColumns}
                    getRowId={(row) => row.id}
                    loading={entriesQuery.isFetching}
                    onPaginationModelChange={gridState.handlePaginationModelChange}
                    onRowClick={(params) => replaceSearchParams({ entryId: params.row.id })}
                    onSortModelChange={gridState.handleSortModelChange}
                    paginationModel={gridState.paginationModel}
                    rowCount={entriesQuery.data?.pagination.total ?? 0}
                    rows={rows}
                    sortModel={gridState.sortModel}
                  />
                </QueryState>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <HarEntryDetailDrawer includeBody={includeBody} row={selectedEntry} />
    </Stack>
  )
}
