import { useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  CardContent,
  Checkbox,
  Divider,
  FormControlLabel,
  Stack,
  Typography,
} from '@mui/material'
import type { GridColDef } from '@mui/x-data-grid'

import type { TestCaseResponse } from '../../shared/api/generated/model'
import { stringifySafe } from '../../shared/lib/json'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { ActiveFilterChips } from '../../shared/ui/ActiveFilterChips'
import { DebouncedTextField } from '../../shared/ui/DebouncedTextField'
import { ExportSnapshotDialog } from '../../shared/ui/ExportSnapshotDialog'
import { FilterToolbar } from '../../shared/ui/FilterToolbar'
import { InvestigationDrawer } from '../../shared/ui/InvestigationDrawer'
import { JsonBlock } from '../../shared/ui/JsonBlock'
import { OperationDetailDrawer } from '../../shared/ui/OperationDetailDrawer'
import { PageHeader } from '../../shared/ui/PageHeader'
import { QueryState } from '../../shared/ui/QueryState'
import { HttpMethodBadge, StatusCodeBadge } from '../../shared/ui/SemanticBadges'
import { SensitiveDataNotice } from '../../shared/ui/SensitiveDataNotice'
import { ServerDataGridPanel } from '../../shared/ui/ServerDataGridPanel'
import { useUrlBackedGridState } from '../../shared/ui/useUrlBackedGridState'
import { TOUR_ANCHORS, tourAnchor } from '../product-tour/tourAnchors'
import { useTestCases } from './api'

export type TestCasesPageSearch = {
  includeBody?: boolean
  limit: number
  offset: number
  operationId?: string
  statusCode?: number
  testCaseId?: string
}

type TestCasesPageProps = {
  runName: string
  search: TestCasesPageSearch
}

type TestCaseRow = TestCaseResponse & {
  id: string
}

function TestCaseDetailDrawer({
  includeBody,
  row,
}: {
  includeBody: boolean
  row?: TestCaseRow
}) {
  const open = Boolean(row)

  function handleClose() {
    replaceSearchParams({ testCaseId: undefined })
  }

  return (
    <InvestigationDrawer
      ariaLabel="Test case detail"
      onClose={handleClose}
      open={open}
      subtitle={row?.test_case_id}
      title="Test case detail"
      data-tour-anchor={TOUR_ANCHORS.testCasesDetail}
    >
      {row ? (
        <Stack spacing={2}>
          <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
            <Button
              onClick={() => replaceSearchParams({ operationId: row.operation_id })}
              size="small"
              variant="outlined"
            >
              {row.operation_id}
            </Button>
            <HttpMethodBadge method={row.http_method} />
            {row.status_code ? <StatusCodeBadge statusCode={row.status_code} /> : null}
            <Typography component="span" sx={{ overflowWrap: 'anywhere' }} variant="body2">
              {row.path ?? ''}
            </Typography>
          </Stack>
          <Divider />
          <Typography component="h3" variant="subtitle2">
            Parameters
          </Typography>
          <JsonBlock maxHeight={180} value={row.parameters ?? {}} />
          {includeBody ? (
            <>
              <SensitiveDataNotice>
                Sanitized test payloads are visible for debugging. Review them before exporting or sharing snapshots.
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

export function TestCasesPage({ runName, search }: TestCasesPageProps) {
  const [exportOpen, setExportOpen] = useState(false)
  const gridState = useUrlBackedGridState(search)
  const includeBody = Boolean(search.includeBody)
  const testCasesQuery = useTestCases(runName, {
    include_body: includeBody,
    limit: search.limit,
    offset: search.offset,
    operation_id: search.operationId,
    status_code: search.statusCode,
  })
  const rows: TestCaseRow[] = (testCasesQuery.data?.items ?? []).map((item) => ({
    ...item,
    id: item.test_case_id,
  }))
  const selectedTestCase = rows.find((row) => row.id === search.testCaseId)
  const testCaseColumns = useMemo<GridColDef<TestCaseRow>[]>(
    () => {
      const columns: GridColDef<TestCaseRow>[] = [
        { field: 'test_case_id', flex: 0.8, headerName: 'Test case', minWidth: 140 },
        {
          field: 'operation_id',
          flex: 1.2,
          headerName: 'Operation',
          minWidth: 180,
          renderCell: (params) => (
            <Button
              onClick={(event) => {
                event.stopPropagation()
                replaceSearchParams({ operationId: params.row.operation_id })
              }}
              size="small"
            >
              {params.row.operation_id}
            </Button>
          ),
        },
        {
          field: 'http_method',
          flex: 0.5,
          headerName: 'Method',
          minWidth: 112,
          renderCell: (params) => <HttpMethodBadge method={params.row.http_method} />,
        },
        { field: 'path', flex: 1, headerName: 'Path', minWidth: 160 },
        {
          field: 'status_code',
          flex: 0.6,
          headerName: 'Status',
          minWidth: 150,
          renderCell: (params) => <StatusCodeBadge statusCode={params.row.status_code} />,
          type: 'number',
        },
        {
          field: 'parameters',
          flex: 1,
          headerName: 'Parameters',
          minWidth: 200,
          valueGetter: (_value, row) => stringifySafe(row.parameters),
        },
      ]

      if (includeBody) {
        columns.push(
          {
            field: 'request_body',
            flex: 1.2,
            headerName: 'Request body',
            minWidth: 240,
            valueGetter: (_value, row) => stringifySafe(row.request_body ?? 'omitted'),
          },
          {
            field: 'response_body',
            flex: 1.2,
            headerName: 'Response body',
            minWidth: 240,
            valueGetter: (_value, row) => stringifySafe(row.response_body ?? 'omitted'),
          },
        )
      }

      return columns
    },
    [includeBody],
  )

  return (
    <Stack spacing={2}>
      <PageHeader
        actions={
          <Button onClick={() => setExportOpen(true)} variant="outlined">
            Export snapshot
          </Button>
        }
        eyebrow="Generated test cases"
        title="Test cases"
        subtitle="Review sanitized request and response examples without persisting payloads into client state."
        {...tourAnchor(TOUR_ANCHORS.testCasesHeader)}
      />

      <Alert severity="info">
        Test case bodies are omitted by default. Enable sanitized backend payloads only when you need body-level debugging.
      </Alert>

      <Card variant="outlined" {...tourAnchor(TOUR_ANCHORS.testCasesResults)}>
        <CardContent>
          <Stack spacing={2}>
            <FilterToolbar>
              <DebouncedTextField
                label="Operation"
                onDebouncedChange={(value) => replaceSearchParams({ offset: 0, operationId: value, testCaseId: undefined })}
                size="small"
                sx={{ minWidth: 220 }}
                value={search.operationId ?? ''}
              />
              <DebouncedTextField
                label="Status"
                onDebouncedChange={(value) => replaceSearchParams({ offset: 0, statusCode: value, testCaseId: undefined })}
                size="small"
                sx={{ minWidth: 120 }}
                value={search.statusCode === undefined ? '' : String(search.statusCode)}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={includeBody}
                    onChange={(event) => {
                      replaceSearchParams({ includeBody: event.target.checked, offset: 0 })
                    }}
                  />
                }
                label="Include sanitized bodies"
              />
            </FilterToolbar>
            <ActiveFilterChips
              filters={[
                { key: 'operationId', label: 'Operation', value: search.operationId },
                { key: 'statusCode', label: 'Status', value: search.statusCode },
                { key: 'testCaseId', label: 'Test case', value: search.testCaseId },
                { key: 'includeBody', label: 'Bodies', value: search.includeBody ? 'included' : undefined },
              ]}
            />
            {includeBody ? (
              <SensitiveDataNotice>
                Sanitized backend payloads are included in the table and drawer for this view only.
              </SensitiveDataNotice>
            ) : null}

            <QueryState
              empty={rows.length === 0}
              error={testCasesQuery.error}
              isError={testCasesQuery.isError}
              isLoading={testCasesQuery.isLoading}
              onRetry={() => void testCasesQuery.refetch()}
            >
              <ServerDataGridPanel
                ariaLabel="test cases"
                columns={testCaseColumns}
                getRowId={(row) => row.id}
                loading={testCasesQuery.isFetching}
                onPaginationModelChange={gridState.handlePaginationModelChange}
                onRowClick={(params) => replaceSearchParams({ testCaseId: params.row.id })}
                onSortModelChange={gridState.handleSortModelChange}
                paginationModel={gridState.paginationModel}
                rowCount={testCasesQuery.data?.pagination.total ?? 0}
                rows={rows}
                sortModel={gridState.sortModel}
              />
            </QueryState>
          </Stack>
        </CardContent>
      </Card>
      <TestCaseDetailDrawer includeBody={includeBody} row={selectedTestCase} />
      <OperationDetailDrawer operationId={search.operationId} runName={runName} />
      <ExportSnapshotDialog
        data={{ test_cases: rows }}
        filters={search}
        onClose={() => setExportOpen(false)}
        open={exportOpen}
        route={`/runs/${encodeURIComponent(runName)}/test-cases`}
        selectedContext={selectedTestCase}
        title="Test cases"
      />
    </Stack>
  )
}
