import { Alert, Button, Card, CardContent, Chip, Grid, Stack, Typography } from '@mui/material'

import type { GraphExplorerEdgeResponse, GraphSequenceResponse } from '../../shared/api/generated/model'
import { replaceSearchParams } from '../../shared/lib/navigation'
import { EvidenceSummaryCard } from '../../shared/ui/EvidenceSummaryCard'
import { StatusSignalStrip } from '../../shared/ui/StatusSignalStrip'

export function DependencyJourneyView({
  edgeRows,
  sequenceRows,
}: {
  edgeRows: GraphExplorerEdgeResponse[]
  sequenceRows: GraphSequenceResponse[]
}) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ alignItems: { md: 'center' } }}>
            <Stack spacing={0.5} sx={{ flex: 1 }}>
              <Typography component="h2" variant="h2">
                Dependency journey
              </Typography>
              <Typography color="text.secondary" variant="body2">
                Sequence-first alternative to the graph canvas for keyboard and screen-reader friendly dependency review.
              </Typography>
            </Stack>
            <StatusSignalStrip
              ariaLabel="Dependency journey signals"
              signals={[
                { label: 'Sequences', tone: sequenceRows.length > 0 ? 'success' : 'neutral', value: sequenceRows.length },
                { label: 'Edges', value: edgeRows.length },
              ]}
            />
          </Stack>

          {sequenceRows.length > 0 ? (
            <Grid container spacing={2}>
              {sequenceRows.map((sequence) => (
                <Grid key={sequence.sequence_id} size={{ xs: 12, lg: 6 }}>
                  <EvidenceSummaryCard
                    actionLabel="Open sequence"
                    badges={
                      <>
                        <Chip label={sequence.sequence_type} size="small" />
                        <Chip label={`${sequence.length} steps`} size="small" variant="outlined" />
                        {sequence.score !== null && sequence.score !== undefined ? (
                          <Chip label={`score ${sequence.score}`} size="small" variant="outlined" />
                        ) : null}
                      </>
                    }
                    description={sequence.operations.join(' -> ')}
                    onAction={() => replaceSearchParams({
                      graphTab: 'sequences',
                      selectedPath: sequence.sequence_id,
                      sequenceId: sequence.sequence_id,
                    })}
                    title={sequence.target_operation_id}
                    tone="success"
                  />
                </Grid>
              ))}
            </Grid>
          ) : (
            <Grid container spacing={2}>
              {edgeRows.map((edge) => (
                <Grid key={edge.edge_id} size={{ xs: 12, lg: 6 }}>
                  <EvidenceSummaryCard
                    badges={
                      <>
                        <Chip label={edge.edge_status} size="small" />
                        <Chip label={`${edge.evidence_count} evidence`} size="small" variant="outlined" />
                      </>
                    }
                    description={`${edge.from_operation_id} -> ${edge.to_operation_id}`}
                    title={edge.edge_id}
                    tone={edge.edge_status === 'final' ? 'success' : 'warning'}
                  />
                </Grid>
              ))}
            </Grid>
          )}
        </Stack>
      </CardContent>
    </Card>
  )
}

export function VisualGraphList({ edgeRows }: { edgeRows: GraphExplorerEdgeResponse[] }) {
  return (
    <Grid aria-label="Navigator edge cards" container spacing={2}>
      {edgeRows.map((edge) => (
        <Grid key={edge.edge_id} size={{ xs: 12, md: 6 }}>
          <EvidenceSummaryCard
            actionLabel="Open edge"
            badges={
              <>
                <Chip label={edge.edge_status} size="small" />
                <Chip label={`${edge.evidence_count} evidence`} size="small" variant="outlined" />
              </>
            }
            description={`${edge.from_operation_id} -> ${edge.to_operation_id}`}
            onAction={() => replaceSearchParams({ edgeId: edge.edge_id })}
            title={edge.edge_id}
            tone={edge.edge_status === 'final' ? 'success' : 'warning'}
          />
        </Grid>
      ))}
    </Grid>
  )
}

export function GraphInspectorPanel({
  encodedRunName,
  pathLabel,
  selectedIncoming,
  selectedNodeId,
  selectedOutgoing,
}: {
  encodedRunName: string
  pathLabel?: string
  selectedIncoming: number
  selectedNodeId: string | null
  selectedOutgoing: number
}) {
  const encodedOperationId = encodeURIComponent(selectedNodeId ?? '')

  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Stack spacing={1.5}>
          <Typography component="h2" variant="h3">
            Navigator inspector
          </Typography>
          {pathLabel ? (
            <Alert severity="info" variant="outlined">
              Selected path: {pathLabel}
            </Alert>
          ) : null}
          {selectedNodeId ? (
            <>
              <Typography sx={{ wordBreak: 'break-word' }}>{selectedNodeId}</Typography>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Chip label={`${selectedIncoming} incoming`} size="small" />
                <Chip label={`${selectedOutgoing} outgoing`} size="small" />
              </Stack>
              <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 1 }}>
                <Button href={`/runs/${encodedRunName}/operations?operationId=${encodedOperationId}`} size="small">
                  Operations
                </Button>
                <Button href={`/runs/${encodedRunName}/constraints?operationId=${encodedOperationId}`} size="small">
                  Constraints
                </Button>
                <Button href={`/runs/${encodedRunName}/reports?operationId=${encodedOperationId}`} size="small">
                  Reports
                </Button>
                <Button href={`/runs/${encodedRunName}/test-cases?operationId=${encodedOperationId}`} size="small">
                  Test cases
                </Button>
              </Stack>
              <Button onClick={() => replaceSearchParams({ operationId: selectedNodeId })} size="small" variant="outlined">
                Open operation detail
              </Button>
            </>
          ) : (
            <Typography color="text.secondary" variant="body2">
              Select a node to inspect its dependency context and related evidence links.
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  )
}
