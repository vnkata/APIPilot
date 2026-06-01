import { Card, CardContent, Chip, Grid, Stack, Typography } from '@mui/material'

import type { OperationExplorerEntryResponse } from '../../shared/api/generated/model'
import { EvidenceSummaryCard } from '../../shared/ui/EvidenceSummaryCard'
import { HttpMethodBadge, StatusCodeBadge } from '../../shared/ui/SemanticBadges'
import { StatusSignalStrip } from '../../shared/ui/StatusSignalStrip'
import { buildOperationMissionBoard } from './operationViewModels'

function OperationEvidenceBadges({ operation }: { operation: OperationExplorerEntryResponse }) {
  return (
    <>
      <HttpMethodBadge method={operation.http_method} />
      {operation.response_statuses.length > 0 ? (
        operation.response_statuses.map((status) => (
          <StatusCodeBadge key={`${operation.operation_key}:${status}`} statusCode={status} />
        ))
      ) : (
        <StatusCodeBadge statusCode={undefined} />
      )}
      <Chip label={`${operation.constraint_count} mapped constraints`} size="small" variant="outlined" />
      <Chip label={`${operation.invariant_count} raw invariant rows`} size="small" variant="outlined" />
      <Chip label={`${operation.test_case_count} test cases`} size="small" variant="outlined" />
      <Chip label={`${operation.graph_in_degree} in / ${operation.graph_out_degree} out`} size="small" variant="outlined" />
    </>
  )
}

function OperationCard({
  onSelect,
  operation,
}: {
  onSelect: (operationKey: string) => void
  operation: OperationExplorerEntryResponse
}) {
  return (
    <EvidenceSummaryCard
      actionLabel={operation.display_operation_id ?? operation.operation_id}
      badges={<OperationEvidenceBadges operation={operation} />}
      description={operation.path_template}
      metric={operation.has_failures ? 'Failures' : 'Clean'}
      onAction={() => onSelect(operation.operation_key)}
      title={operation.operation_id}
      tone={operation.has_failures ? 'danger' : 'success'}
    />
  )
}

export function OperationCardsView({
  onSelect,
  rows,
}: {
  onSelect: (operationKey: string) => void
  rows: OperationExplorerEntryResponse[]
}) {
  return (
    <Grid aria-label="Operation cards" component="section" container role="region" spacing={2}>
      {rows.map((operation) => (
        <Grid key={operation.operation_key} size={{ xs: 12, md: 6, xl: 4 }}>
          <OperationCard onSelect={onSelect} operation={operation} />
        </Grid>
      ))}
    </Grid>
  )
}

export function OperationEvidenceCanvas({
  onSelect,
  rows,
}: {
  onSelect: (operationKey: string) => void
  rows: OperationExplorerEntryResponse[]
}) {
  const board = buildOperationMissionBoard(rows)

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' } }}>
        <Stack spacing={0.5} sx={{ flex: 1 }}>
          <Typography component="h2" variant="h2">
            Operation Mission Board
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Triage the visible server-paginated result set by failures, dependency pressure, mapped constraints, and evidence readiness.
          </Typography>
        </Stack>
        <StatusSignalStrip
          ariaLabel="Operation evidence signals"
          signals={[
            { label: 'Failures', tone: board.metrics.failures > 0 ? 'danger' : 'success', value: board.metrics.failures },
            { label: 'Graph linked', tone: board.metrics.graphLinked > 0 ? 'success' : 'neutral', value: board.metrics.graphLinked },
            { label: 'Low evidence', tone: board.metrics.lowEvidence > 0 ? 'warning' : 'success', value: board.metrics.lowEvidence },
            { label: 'Visible', value: board.metrics.visible },
          ]}
        />
      </Stack>

      <Grid container spacing={2}>
        {board.lanes.map((lane) => (
          <Grid key={lane.id} size={{ xs: 12, lg: lane.id === 'failures' ? 12 : 6, xl: 4 }}>
            <Card variant="outlined" sx={{ height: '100%' }}>
              <CardContent>
                <Stack spacing={1.5}>
                  <Stack spacing={0.5}>
                    <Typography component="h3" variant="h3">
                      {lane.title}
                    </Typography>
                    <Typography color="text.secondary" variant="body2">
                      {lane.description}
                    </Typography>
                  </Stack>
                  {lane.operations.length > 0 ? (
                    lane.operations.map((operation) => (
                      <OperationCard key={operation.operation_key} onSelect={onSelect} operation={operation} />
                    ))
                  ) : (
                    <Typography color="text.secondary" variant="body2">
                      No visible operations in this lane.
                    </Typography>
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  )
}
